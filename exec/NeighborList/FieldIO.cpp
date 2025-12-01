#include "FieldIO.H"
#include "MDParticleContainer.H"

#include <AMReX_BoxArray.H>
#include <AMReX_DistributionMapping.H>
#include <AMReX_Geometry.H>
#include <AMReX_MultiFab.H>
#include <AMReX_PlotFileUtil.H>
#include <AMReX_Vector.H>

#include <memory>
#include <string>
#include <fstream>   

using namespace amrex;

void WritePlotFile (const MDParticleContainer& pc,
                    const Vector<Geometry>& geom,
                    int nstep)
{
    // ------------------------------------------------------------------
    // 1. Build a very simple grid dataset: 1-component MultiFab of zeros
    // ------------------------------------------------------------------
    const int num_levels = geom.size();
    if (num_levels <= 0) {
        return;  // nothing to do
    }

    // One component called "dummy" just so yt has something to read
    Vector<std::string> varnames(1);
    varnames[0] = "dummy";

    // Time step numbers (all equal to nstep)
    Vector<int> level_steps(num_levels, nstep);

    // MultiFabs per level
    Vector<std::unique_ptr<MultiFab>> mf(num_levels);
    Vector<const MultiFab*> output_cc(num_levels);

    for (int lev = 0; lev < num_levels; ++lev) {
        // Single BoxArray covering the whole domain at this level
        BoxArray ba(geom[lev].Domain());
        DistributionMapping dm(ba);

        mf[lev] = std::make_unique<MultiFab>(ba, dm, varnames.size(), 0);
        mf[lev]->setVal(0.0);  // fill with zeros

        output_cc[lev] = mf[lev].get();
    }

    // Refinement ratio between levels (dummy 2:1 if you ever have >1 level)
    Vector<IntVect> refRatio(std::max(num_levels - 1, 0));
    for (int lev = 0; lev < num_levels - 1; ++lev) {
        refRatio[lev] = IntVect(AMREX_D_DECL(2, 2, 2));
    }

    // Plotfile name: plt00000, plt00001, ...
    const std::string pltfile = amrex::Concatenate("plt", nstep, 5);

    // ------------------------------------------------------------------
    // 2. Write the grid plotfile (this creates pltXXXXX/Header, Level_0...)
    // ------------------------------------------------------------------
    WriteMultiLevelPlotfile(pltfile,
                            num_levels,
                            output_cc,
                            varnames,
                            geom,
                            /*time=*/0.0,
                            level_steps,
                            refRatio);

    // ------------------------------------------------------------------
    // 3. Write the particle checkpoint inside the same plotfile dir
    //    This will create pltXXXXX/particle0/{Header, DATA_00000, Particle_H}
    // ------------------------------------------------------------------
    Vector<std::string> particle_varnames(PIdx::ncomps);
    particle_varnames[PIdx::vx] = "vx";
    particle_varnames[PIdx::vy] = "vy";
    particle_varnames[PIdx::vz] = "vz";
    particle_varnames[PIdx::ax] = "ax";
    particle_varnames[PIdx::ay] = "ay";
    particle_varnames[PIdx::az] = "az";

    pc.Checkpoint(pltfile, "particle0", true, particle_varnames);
}

void WriteParticlesVTK (const MDParticleContainer& pc,
                        int nstep)
{
    using ParticleType = MDParticleContainer::ParticleType;

    // ------------------------------------------------------------------
    // 1. Count total number of particles across all levels
    // ------------------------------------------------------------------
    amrex::Long np_total = 0;
    const int finest_level = pc.finestLevel();

    for (int lev = 0; lev <= finest_level; ++lev) {
        const auto& plev = pc.GetParticles(lev);
        for (auto const& kv : plev) {
            const auto& ptile = kv.second;
            np_total += ptile.GetArrayOfStructs().numParticles();
        }
    }

    if (np_total == 0) {
        amrex::Print() << "WriteParticlesVTK: no particles to write.\n";
        return;
    }

    // ------------------------------------------------------------------
    // 2. Collect particle data into host vectors
    // ------------------------------------------------------------------
    amrex::Vector<amrex::Real> xs, ys, zs;
    amrex::Vector<amrex::Real> vxs, vys, vzs;
    amrex::Vector<amrex::Real> axs, ays, azs;

    xs.reserve(np_total); ys.reserve(np_total); zs.reserve(np_total);
    vxs.reserve(np_total); vys.reserve(np_total); vzs.reserve(np_total);
    axs.reserve(np_total); ays.reserve(np_total); azs.reserve(np_total);

    for (int lev = 0; lev <= finest_level; ++lev) {
        const auto& plev = pc.GetParticles(lev);
        for (auto const& kv : plev) {
            const auto& ptile = kv.second;
            const auto& aos   = ptile.GetArrayOfStructs();
            const std::size_t np = aos.numParticles();

            const ParticleType* p = aos().dataPtr();

            for (std::size_t i = 0; i < np; ++i) {
                const ParticleType& part = p[i];

                xs.push_back(part.pos(0));
                ys.push_back(part.pos(1));
                zs.push_back(part.pos(2));

                vxs.push_back(part.rdata(PIdx::vx));
                vys.push_back(part.rdata(PIdx::vy));
                vzs.push_back(part.rdata(PIdx::vz));

                axs.push_back(part.rdata(PIdx::ax));
                ays.push_back(part.rdata(PIdx::ay));
                azs.push_back(part.rdata(PIdx::az));
            }
        }
    }

    // ------------------------------------------------------------------
    // 3. Open VTK file
    // ------------------------------------------------------------------
    const std::string vtkfile =
        amrex::Concatenate("particles_", nstep, 5) + ".vtk";

    std::ofstream ofs(vtkfile);
    if (!ofs.good()) {
        amrex::Print() << "WriteParticlesVTK: could not open file "
                       << vtkfile << "\n";
        return;
    }

    // ------------------------------------------------------------------
    // 4. Write legacy VTK PolyData header
    // ------------------------------------------------------------------
    ofs << "# vtk DataFile Version 3.0\n";
    ofs << "MD particles\n";
    ofs << "ASCII\n";
    ofs << "DATASET POLYDATA\n";

    // POINTS section
    ofs << "POINTS " << np_total << " double\n";
    for (amrex::Long i = 0; i < np_total; ++i) {
        ofs << xs[i] << " " << ys[i] << " " << zs[i] << "\n";
    }
    ofs << "\n";

    // Optionally, define vertices so that each point is its own vertex
    ofs << "VERTICES " << np_total << " " << 2 * np_total << "\n";
    for (amrex::Long i = 0; i < np_total; ++i) {
        ofs << "1 " << i << "\n";
    }
    ofs << "\n";

    // ------------------------------------------------------------------
    // 5. Attach particle data as POINT_DATA
    // ------------------------------------------------------------------
    ofs << "POINT_DATA " << np_total << "\n";

    auto write_scalar = [&] (const std::string& name,
                             const amrex::Vector<amrex::Real>& data)
    {
        ofs << "SCALARS " << name << " double 1\n";
        ofs << "LOOKUP_TABLE default\n";
        for (amrex::Long i = 0; i < np_total; ++i) {
            ofs << data[i] << "\n";
        }
        ofs << "\n";
    };

    write_scalar("vx", vxs);
    write_scalar("vy", vys);
    write_scalar("vz", vzs);
    write_scalar("ax", axs);
    write_scalar("ay", ays);
    write_scalar("az", azs);

    ofs.close();

    amrex::Print() << "WriteParticlesVTK: wrote " << np_total
                   << " particles to " << vtkfile << "\n";
}


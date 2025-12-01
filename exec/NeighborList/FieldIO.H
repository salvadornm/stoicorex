#ifndef FIELD_IO_H_
#define FIELD_IO_H_

#include "MDParticleContainer.H"

#include <AMReX_Geometry.H>
#include <AMReX_MultiFab.H>
#include <AMReX_Vector.H>

#include <array>

void WritePlotFile (const MDParticleContainer& pc,
                    const amrex::Vector<amrex::Geometry>& geom,
                    int nstep);

// NEW: write all particles to a VTK polydata file
void WriteParticlesVTK (const MDParticleContainer& pc,
                        int nstep);


#endif

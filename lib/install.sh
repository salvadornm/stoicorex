AMREXVERSION=25.11
PELEPVERSION=23.03
#dir= $PWD
case  $1 in
	git )
		echo " installing git versions .. "
		gh repo clone AMReX-Combustion/PelePhysics
		;;
	safe )
    rm -rf amrex
		echo " installing AMREX release version .." $AMREXVERSION
		wget https://github.com/AMReX-Codes/amrex/archive/refs/tags/$AMREXVERSION.zip
		unzip $AMREXVERSION.zip
    mv amrex-$AMREXVERSION amrex
		rm $AMREXVERSION.zip
    rm -rf PelePhysics
    echo " installing PelePhysics release version .." $PELEPVERSION
    wget https://github.com/AMReX-Combustion/PelePhysics/archive/refs/tags/v$PELEPVERSION.zip
    unzip v$PELEPVERSION.zip
    mv PelePhysics-$PELEPVERSION PelePhysics
    rm v$PELEPVERSION.zip
    ;;
	amrex)
		rm -rf amrex
		echo " installing AMREX release version .." $AMREXVERSION
		wget https://github.com/AMReX-Codes/amrex/archive/refs/tags/$AMREXVERSION.zip
		unzip $AMREXVERSION.zip
    mv amrex-$AMREXVERSION amrex
		rm $AMREXVERSION.zip	
		;;
	pelephys)
		rm -rf PelePhysics
    echo " installing PelePhysics release version .." $PELEPVERSION
    wget https://github.com/AMReX-Combustion/PelePhysics/archive/refs/tags/v$PELEPVERSION.zip        
    unzip v$PELEPVERSION.zip
    mv PelePhysics-$PELEPVERSION PelePhysics 
		rm v$PELEPVERSION.zip
		;;
  autodiff)
    git submodule update --init --recursive autodiff
    rm -rf build/autodiff
    mkdir -p ./build/autodiff
    cd build/autodiff
    cmake ../../autodiff/ -DCMAKE_INSTALL_PREFIX=../../install/autodiff
    ;;
  clad)
    git submodule update --init --recursive clad
    mkdir -p build/clad
    mkdir -p install/clad
    cd build/clad
    cmake ../../clad/ -DClang_DIR=/usr/lib/llvm-11 -DLLVM_DIR=/usr/lib/llvm-11 -DCMAKE_INSTALL_PREFIX=../../install/clad -DLLVM_EXTERNAL_LIT="$(which lit)"
    make && make install
    ;;
  *)
	  echo " no option selected [git/safe/amrex/pelephys]"
    echo "Options:"
	  echo "  git           Install using git clone latest AMREX+PelePhysics"    
    echo "  safe          Install using release versions of AMREX+PelePhysics"
    echo "  amrex         Install AMREX release version: $AMREXVERSION "
    echo "  pelephys      Install PelePhysics release version: $PELEPVERSION "
    exit
esac
echo -e "\\033[1;32m  Installation done \\033[0m"

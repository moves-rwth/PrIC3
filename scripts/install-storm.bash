set -e # fail on errors

mkdir -p deps
cd deps

# storm dependencies
apt-get install -y git cmake libboost-all-dev libcln-dev libgmp-dev libginac-dev automake libglpk-dev libhwloc-dev
apt-get install -y libz3-dev libxerces-c-dev libeigen3-dev

# storm itself
if [ ! -d "storm" ]; then
  git clone https://github.com/moves-rwth/storm.git
  cd storm
  mkdir build
else
  cd storm
  git fetch --all
fi

git checkout 1.5.1

# If we don't have at least 4 GB of RAM, use just one CPU core.
MEM_AVAILABLE="$(awk '/^MemAvailable:/ { print $2; }' /proc/meminfo)"
if [[ -n "$MEM_AVAILABLE" && "$MEM_AVAILABLE" -lt 4194304 ]]; then
  MAKE_PARAMS="-j1"
else
  MAKE_PARAMS="-j$(nproc)"
fi

# In CI, compile in debug mode.
if [[ -n "$CI" ]]; then
  CMAKE_PARAMS="-DSTORM_USE_LTO=OFF -DSTORM_DEVELOPER=ON"
else
  CMAKE_PARAMS=""
fi

cd build

set -x # print commands
cmake $CMAKE_PARAMS ..
make $MAKE_PARAMS

# add a symbolic link in the repo root
cd ../..
ln -s deps/storm/build/bin/storm storm

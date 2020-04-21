set -e # fail on errors

apt-get install -y python3-pip

pip3 install virtualenv

if [[ "$VIRTUAL_ENV" == "" ]]; then
  virtualenv -p python3 env_python
  source env_python/bin/activate
fi

# We must do this manually, because stormpy's setup.py
# won't install pycarl automatically if debug is enabled.
# Instead setup.py will crash with a really confusing error message.
pip3 install pycarl

mkdir -p deps
cd deps

if [ ! -d "stormpy" ]; then
  git clone https://github.com/moves-rwth/stormpy.git
  cd stormpy
  mkdir build
else
  cd stormpy
  git pull origin master
fi

git checkout e30b7da2e943060e0e95e34a32595d2bdfda0710

# If we don't have at least 4 GB of RAM, use just one CPU core.
MEM_AVAILABLE="$(awk '/^MemAvailable:/ { print $2; }' /proc/meminfo)"
if [[ -n "$MEM_AVAILABLE" && "$MEM_AVAILABLE" -lt 4194304 ]]; then
  BUILD_PARAMS="--jobs 1"
else
  BUILD_PARAMS=""
fi

# In CI, compile in debug mode.
if [[ -n "$CI" ]]; then
  BUILD_PARAMS="$BUILD_PARAMS --debug"
fi

set -x # print commands

# Omit DFT and parametric models for faster builds
# TODO: remove "develop"?
python3 setup.py build_ext --disable-dft --disable-pars $BUILD_PARAMS develop

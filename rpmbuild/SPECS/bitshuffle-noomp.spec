Name:           bitshuffle-noomp
Version:        0.5.2
Release:        1%{?dist}
Summary:        PSI DataHub application

License:        GPLv3
URL:            https://github.com/kiyo-masui/bitshuffle
Source0:        bitshuffle-0.5.2-noomp.tar.gz
BuildArch:      noarch

Requires:       python3
Requires:       python3-pip
Requires:       python3-devel
Requires:       gcc
Requires:       gcc-c++
Requires:       hdf5-devel


%description
Bitshuffle filter for improving compression of typed binary data.
This package installs Bitshuffle with OpenMP disabled.

%prep
%setup -q -n bitshuffle-0.5.2

%build
# nothing to build

%install
rm -rf %{buildroot}

# Install vendored sources into /usr/local/src
install -d %{buildroot}/usr/local/src/bitshuffle-noomp
cp -a * %{buildroot}/usr/local/src/bitshuffle-noomp/

%files
/usr/local/src/bitshuffle-noomp

%post
echo "Installing bitshuffle without OpenMP..."

cd /usr/local/src/bitshuffle-noomp

CFLAGS="-O3" CXXFLAGS="-O3" \
/usr/bin/python3 -m pip install --index-url=https://pypi.psi.ch/simple .

%postun
if [ $1 -eq 0 ]; then
    echo "Uninstalling bitshuffle..."
    /usr/bin/python3 -m pip uninstall -y bitshuffle || true
fi
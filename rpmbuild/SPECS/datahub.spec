Name:           datahub
Version:        1.1.9
Release:        1%{?dist}
Summary:        PSI DataHub application

License:        GPLv3
URL:            https://github.com/paulscherrerinstitute/datahub
Source0:        datahub-launcher.sh
BuildArch:      noarch

Requires:       python3
Requires:       python3-pip
Requires:       python3-devel
#python3-devel needed to compile bitshuffle

#BuildRequires:  python3
#BuildRequires:  python3-pip

%description
DataHub application and supporting Python libraries.

This package installs the DataHub Python library into the system
Python and provides a launcher script.

%prep
# nothing to prep

%build
# nothing to build

%install
rm -rf %{buildroot}

# Install launcher
install -d %{buildroot}/usr/local/bin
install -m 0755 %{SOURCE0} %{buildroot}/usr/local/bin/datahub

#install -m 0755 %{SOURCE0} %{buildroot}/usr/local/bin/datahub-%{version}
## Create stable symlink
#cd %{buildroot}/usr/local/bin
#ln -s datahub-%{version} %{buildroot}/usr/local/bin/datahub

%files
/usr/local/bin/datahub
#/usr/local/bin/datahub-%{version}

%post
# Install dependencies  without upgrading anything
/usr/bin/python3 -m pip install \
  --index-url=https://pypi.psi.ch/simple \
  --upgrade-strategy only-if-needed \
  psi-pshell psi-bsread \
  numpy h5py requests cbor2 pyepics pyzmq redis websockets \
  python-dateutil pytz pandas matplotlib sseclient

#Upgrade datahub
/usr/bin/python3 -m pip install \
  --index-url=https://pypi.psi.ch/simple \
  --upgrade \
  psi-datahub==%{version}


%postun
/usr/bin/python3 -m pip uninstall -y psi-datahub


%changelog
* Tue Jan 27 2026 Alexandre Gobbo <alexandre.gobbo@psi.ch> - 1.1.5-1
- Initial RPM release
# Run after Build/Prepare/Default has applied all feed patches.
define Miniupnpd/ApplyOfficialFixes
	python3 "$(CURDIR)/miniupnpd-backports/backport.py" "$(PKG_BUILD_DIR)" --version "$(PKG_VERSION)" --release "$(PKG_RELEASE)" --variant "$(BUILD_VARIANT)"
endef
Hooks/Prepare/Post += Miniupnpd/ApplyOfficialFixes

define Miniupnpd/VerifyOfficialFixes
	python3 "$(CURDIR)/miniupnpd-backports/backport.py" "$(PKG_BUILD_DIR)" --verify-only
endef
Hooks/Compile/Pre += Miniupnpd/VerifyOfficialFixes

define Miniupnpd/PublishSourceReceipt
	$(CP) "$(PKG_BUILD_DIR)/miniupnpd-backports.json" "$(TOPDIR)/miniupnpd-$(BUILD_VARIANT)-backports.json"
endef
Hooks/Compile/Post += Miniupnpd/PublishSourceReceipt

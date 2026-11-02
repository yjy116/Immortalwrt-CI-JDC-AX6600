# Run after Build/Prepare/Default has applied all feed patches.
MINIUPNPD_FIX_SOURCE = $(PKG_BUILD_DIR)/$(CONFIGURE_PATH)
define Miniupnpd/ApplyOfficialFixes
	python3 "$(CURDIR)/miniupnpd-backports/backport.py" "$(MINIUPNPD_FIX_SOURCE)" --version "$(PKG_VERSION)" --release "$(PKG_RELEASE)" --variant "$(BUILD_VARIANT)" --source-commit "$(PKG_SOURCE_VERSION)" --archive-sha256 "$(PKG_HASH)"
endef
Hooks/Prepare/Post += Miniupnpd/ApplyOfficialFixes

define Miniupnpd/VerifyOfficialFixes
	python3 "$(CURDIR)/miniupnpd-backports/backport.py" "$(MINIUPNPD_FIX_SOURCE)" --verify-only
endef
Hooks/Compile/Pre += Miniupnpd/VerifyOfficialFixes

define Miniupnpd/PublishSourceReceipt
	$(CP) "$(MINIUPNPD_FIX_SOURCE)/miniupnpd-backports.json" "$(TOPDIR)/miniupnpd-$(BUILD_VARIANT)-backports.json"
endef
Hooks/Compile/Post += Miniupnpd/PublishSourceReceipt

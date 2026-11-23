store_boot_preference() {
	local command=disable
	[ "$1" = 1 ] && command=enable
	uci set "honk.main.boot_enabled=$1" && uci commit honk && /etc/init.d/honk "$command"
}

boot_settings() {
	local request requested kind old
	request=$(cat)
	json_load "$request" 2>/dev/null || { emit_result false invalid_request; return 1; }
	json_get_var requested boot_enabled
	json_get_type kind boot_enabled
	case "$kind:$requested" in boolean:0|boolean:1) ;; *) emit_result false invalid_boolean_settings; return 1 ;; esac
	honk_lock_acquire || { emit_result false operation_in_progress; return 1; }
	trap 'honk_lock_release >/dev/null 2>&1' 0
	if [ -e /etc/.honk-maintenance/journal ] || [ -L /etc/.honk-maintenance/journal ]; then
		emit_result false maintenance_recovery_required; return 1
	fi
	if [ -e /etc/.honk-update/journal ] || [ -L /etc/.honk-update/journal ]; then
		emit_result false update_recovery_required; return 1
	fi
	old=$(uci -q get honk.main.boot_enabled) || { emit_result false boot_preference_unavailable; return 1; }
	case "$old" in 0|1) ;; *) emit_result false invalid_boolean_settings; return 1 ;; esac
	if store_boot_preference "$requested"; then emit_result true settings_saved; return 0; fi
	if ! store_boot_preference "$old"; then emit_result false boot_update_and_rollback_failed; return 1; fi
	emit_result false boot_update_failed_rolled_back
	return 1
}

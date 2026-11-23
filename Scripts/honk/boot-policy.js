'use strict';
'require view';
'require rpc';

const readBoot = rpc.declare({ object: 'honk', method: 'status', expect: { '': {} } });
const saveBoot = rpc.declare({
	object: 'honk', method: 'boot_settings', params: ['boot_enabled'], expect: { '': {} }
});

function saveHandler({ input, button, message }) {
	let busy = false;
	return async function(event) {
		event.preventDefault();
		if (busy)
			return;
		busy = input.disabled = button.disabled = true;
		message.textContent = '';
		try {
			const result = await saveBoot(input.checked);
			if (result?.ok !== true)
				throw new Error(result?.message || _('Unable to save Honk boot preference.'));
			message.textContent = _('Settings saved.');
		} catch (error) {
			message.textContent = error.message || String(error);
		} finally {
			busy = input.disabled = button.disabled = false;
		}
	};
}

return view.extend({
	load: function() { return readBoot(); },
	render: function(status) {
		if (typeof status?.boot_enabled !== 'boolean')
			throw new Error(_('Honk boot preference is unavailable.'));

		const input = E('input', { type: 'checkbox', id: 'honk-boot-enabled' });
		input.checked = status.boot_enabled;
		const button = E('button', { type: 'submit', class: 'cbi-button cbi-button-positive' }, _('Save'));
		const message = E('p', { role: 'status' });
		const form = E('form', {}, [
			E('label', { for: 'honk-boot-enabled' }, [input, ' ', _('Start on boot')]),
			E('p', {}, [button]),
			message
		]);
		form.addEventListener('submit', saveHandler({ input, button, message }));
		return E('div', { class: 'cbi-map' }, [E('h2', {}, _('Boot policy')), form]);
	},
	handleSave: null,
	handleSaveApply: null,
	handleReset: null
});

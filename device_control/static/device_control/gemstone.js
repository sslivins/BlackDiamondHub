/* Gemstone Lights controls — power on/off + saved-pattern picker.
   Wired to the real backend:
     GET  api/gemstone/states/   -> { configured, devices:[…], patterns:[…] }  (or { configured, error })
     POST api/gemstone/action/   body { device_id, action, value }  -> { ok, device:{…} }

   The control surface is intentionally small: each discovered device gets a
   power toggle and a grid of the account's saved patterns; tapping a pattern
   plays it (and implies power-on). All selectors are scoped under
   #panel-gemstone. */
(function () {
    const ROOT = document.getElementById('panel-gemstone');
    if (!ROOT) return;  // gemstone tab not present

    const STATES_URL = ROOT.dataset.statesUrl;
    const ACTION_URL = ROOT.dataset.actionUrl;
    const CSRF = ROOT.dataset.csrf;

    // raw backend records + transient state
    let DEVICES = [];
    let PATTERNS = [];
    let configured = true;
    let loadError = null;
    let editing = false;   // true briefly while an action is in flight

    const sels = {
        status: ROOT.querySelector('#gemStatus'),
        devices: ROOT.querySelector('#gemDevices'),
    };

    // ── helpers ──────────────────────────────────────────────
    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    function swatches(colors, max) {
        const list = Array.isArray(colors) ? colors.slice(0, max || 10) : [];
        if (!list.length) return '';
        return `<div class="gem-swatches">${list.map(c =>
            `<span class="gem-sw" style="background:${esc(c)}"></span>`).join('')}</div>`;
    }

    function statusText(d) {
        if (!d.online) return 'Offline';
        if (!d.power) return 'Off';
        return d.pattern_name ? esc(d.pattern_name) : 'On';
    }

    // ── network ──────────────────────────────────────────────
    function sendAction(deviceId, action, value) {
        editing = true;
        return fetch(ACTION_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
            body: JSON.stringify({ device_id: deviceId, action, value }),
        })
            .then(r => r.json().then(d => ({ ok: r.ok, d })))
            .then(({ ok, d }) => {
                if (ok && d && d.device) {
                    const idx = DEVICES.findIndex(x => x.id === d.device.id);
                    if (idx >= 0) DEVICES[idx] = d.device;
                    render();
                } else if (!ok) {
                    console.error('gemstone action failed', action, d);
                }
            })
            .catch(err => console.error('gemstone action error', action, err))
            .finally(() => { editing = false; });
    }

    function fetchStates() {
        return fetch(STATES_URL)
            .then(r => r.json())
            .then(data => {
                configured = data.configured !== false;
                loadError = data.error || null;
                DEVICES = Array.isArray(data.devices) ? data.devices : [];
                PATTERNS = Array.isArray(data.patterns) ? data.patterns : [];
                render();
            })
            .catch(err => {
                console.error('gemstone states error', err);
                loadError = 'Could not reach the Gemstone service.';
                render();
            });
    }

    // ── render ───────────────────────────────────────────────
    function showMessage(html) {
        sels.status.innerHTML = '';
        sels.devices.innerHTML = `<div class="gem-msg">${html}</div>`;
    }

    function deviceCard(d) {
        const online = !!d.online;
        const on = !!d.power;
        const dotCls = online ? 'online' : 'offline';
        const patterns = PATTERNS.map(p => {
            const active = on && d.pattern_id && p.id === d.pattern_id;
            return `
            <button class="gem-pat ${active ? 'active' : ''}" data-pattern="${esc(p.id)}"
                    title="${esc(p.name)}" ${online ? '' : 'disabled'}>
                ${swatches(p.colors, 6)}
                <span class="gem-pat-name">${p.is_favorite ? '<i class="fa-solid fa-star"></i> ' : ''}${esc(p.name)}</span>
            </button>`;
        }).join('');

        const patternsBlock = PATTERNS.length
            ? `<div class="gem-pats">${patterns}</div>`
            : `<div class="gem-empty">No saved patterns on this account.</div>`;

        return `
        <div class="gem-card ${on ? 'on' : ''}" data-id="${esc(d.id)}">
            <div class="gem-head">
                <div class="gem-ic"><i class="fa-solid fa-gem"></i></div>
                <div class="gem-meta">
                    <b>${esc(d.name) || 'Gemstone'}</b>
                    <span><span class="dot ${dotCls}">●</span>${statusText(d)}</span>
                </div>
                <button class="gem-power ${on ? 'on' : ''}" data-power
                        ${online ? '' : 'disabled'} aria-label="Power">
                    <i class="fa-solid fa-power-off"></i>
                </button>
            </div>
            ${d.pattern_name && on ? `<div class="gem-current">${swatches(d.pattern_colors, 12)}<span>${esc(d.pattern_name)}</span></div>` : ''}
            ${patternsBlock}
        </div>`;
    }

    function render() {
        if (!configured) {
            showMessage('<i class="fa-solid fa-circle-info"></i> Gemstone cloud is not configured. Set GEMSTONE_EMAIL and GEMSTONE_PASSWORD on the server.');
            return;
        }
        if (loadError) {
            showMessage(`<i class="fa-solid fa-triangle-exclamation"></i> ${esc(loadError)}`);
            return;
        }
        if (!DEVICES.length) {
            showMessage('<i class="fa-solid fa-gem"></i> No Gemstone devices found on this account.');
            return;
        }
        sels.status.innerHTML = '';
        sels.devices.innerHTML = DEVICES.map(deviceCard).join('');
        wire();
    }

    function wire() {
        sels.devices.querySelectorAll('.gem-card').forEach(card => {
            const id = card.dataset.id;
            const dev = DEVICES.find(x => x.id === id);
            if (!dev) return;

            const powerBtn = card.querySelector('[data-power]');
            if (powerBtn) powerBtn.onclick = () => {
                const next = !dev.power;
                dev.power = next;            // optimistic
                render();
                sendAction(id, 'power', next);
            };

            card.querySelectorAll('[data-pattern]').forEach(el => el.onclick = () => {
                const pid = el.dataset.pattern;
                const pat = PATTERNS.find(p => p.id === pid);
                dev.power = true;            // playing a pattern implies on
                dev.pattern_id = pid;
                if (pat) {
                    dev.pattern_name = pat.name;
                    dev.pattern_colors = pat.colors;
                }
                render();
                sendAction(id, 'pattern', pid);
            });
        });
    }

    // ── poll — skip while an action is in flight ─────────────
    function poll() {
        if (editing) return;
        if (!ROOT.classList.contains('active')) return;
        fetchStates();
    }

    // initial load + 9s refresh
    showMessage('<i class="fa-solid fa-spinner fa-spin"></i> Loading Gemstone…');
    fetchStates();
    setInterval(poll, 9000);
})();

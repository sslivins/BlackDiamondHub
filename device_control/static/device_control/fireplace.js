/* Napoleon fireplace controls — ported from fireplace_mockup_v3.html and
   wired to the real backend:
     GET  api/fireplace/states/   -> { configured, fireplaces:[ state… ] }  (or { configured, error })
     POST api/fireplace/action/   body { dsn, action, value }  -> { ok, fireplace:{…} }

   The backend state dict uses different field names than the mockup; toView()
   adapts a backend record into the mockup-shaped object the render code expects,
   and the *_ACTION / RAW_FIELD maps translate UI changes back to backend
   actions + cached-field writes. RGB is [r,g,b] on the wire, hex in the UI. */
(function () {
    const ROOT = document.getElementById('panel-fireplace');
    if (!ROOT) return;  // fireplace tab not present

    const STATES_URL = ROOT.dataset.statesUrl;
    const ACTION_URL = ROOT.dataset.actionUrl;
    const CSRF = ROOT.dataset.csrf;

    const PRESETS = [
        { slot: "partytime", name: "Party Time", icon: "fa-champagne-glasses" },
        { slot: "campfirewarmth", name: "Campfire", icon: "fa-campground" },
        { slot: "summerday", name: "Summer Day", icon: "fa-sun" },
        { slot: "glowingsunset", name: "Sunset", icon: "fa-mountain-sun" },
    ];
    const HEATER = ["Off", "Low", "High"];

    // mockup-key -> backend action name (for sliders/steppers)
    const SET_ACTION = { flame_speed: 'flame_speed', orange_flame: 'orange_flame',
                         yellow_flame: 'yellow_flame', ember_bri: 'ember_bed_brightness' };
    // mockup-flag -> backend action name (booleans; top_on handled specially)
    const FLAG_ACTION = { eco: 'eco_mode', boost: 'boost_mode',
                          top_cycle: 'top_light_cycling', ember_cycle: 'ember_bed_cycling' };
    // mockup-color -> backend action name
    const COLOR_ACTION = { top_rgb: 'top_light_rgb', ember_rgb: 'ember_bed_rgb' };
    // mockup-key -> backend cached-state field name (to mutate STATES optimistically)
    const RAW_FIELD = {
        flame_speed: 'flame_speed', orange_flame: 'orange_flame', yellow_flame: 'yellow_flame',
        ember_bri: 'ember_bed_brightness', eco: 'eco_mode', boost: 'boost_mode',
        top_cycle: 'top_light_cycling', ember_cycle: 'ember_bed_cycling',
        top_rgb: 'top_light_rgb', ember_rgb: 'ember_bed_rgb',
    };

    // raw backend records, current selection, open popover, transient-edit guard
    let STATES = [];
    let configured = true;
    let loadError = null;
    let sel = 0;
    let openPop = null;
    let editing = false;   // true while a slider/color picker is being dragged

    const sels = {
        select: ROOT.querySelector('#fpSelect'),
        preview: ROOT.querySelector('#preview'),
        presets: ROOT.querySelector('#presetsBar'),
    };

    // ── helpers ──────────────────────────────────────────────
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
    function isArr3(a) { return Array.isArray(a) && a.length === 3; }
    function rgbArrToHex(a) {
        if (!isArr3(a)) return '#ff5a1e';
        return '#' + a.map(x => clamp(+x | 0, 0, 255).toString(16).padStart(2, '0')).join('');
    }
    function hexToRgbArr(hex) {
        const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex || '');
        return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [255, 90, 30];
    }
    function isNonBlack(a) { return isArr3(a) && (a[0] | a[1] | a[2]) > 0; }

    // backend record -> mockup-shaped view object used by the render code
    function toView(s) {
        return {
            dsn: s.dsn,
            name: s.name || s.dsn,
            online: s.online !== false,           // null (unknown) and true both render as online-ish
            power: !!s.power,
            flame_speed: s.flame_speed == null ? 1 : s.flame_speed,
            orange_flame: s.orange_flame == null ? 0 : s.orange_flame,
            yellow_flame: s.yellow_flame == null ? 0 : s.yellow_flame,
            heater: s.heater == null ? 0 : s.heater,
            setpoint_c: s.setpoint_c == null ? 20 : s.setpoint_c,
            eco: !!s.eco_mode,
            boost: !!s.boost_mode,
            ember_rgb: rgbArrToHex(s.ember_bed_rgb),
            ember_bri: s.ember_bed_brightness == null ? 0 : s.ember_bed_brightness,
            ember_cycle: !!s.ember_bed_cycling,
            top_rgb: rgbArrToHex(s.top_light_rgb),
            top_cycle: !!s.top_light_cycling,
            top_on: isNonBlack(s.top_light_rgb),
            favourite: s.current_favourite || null,
        };
    }
    function view() { return toView(STATES[sel]); }

    function statusText(f) {
        if (!f.online) return "Offline";
        if (!f.power) return "Standby";
        return `On · ${f.setpoint_c}°C · Flame ${f.flame_speed}`;
    }

    // ── network ──────────────────────────────────────────────
    function sendAction(action, value) {
        const dsn = STATES[sel] && STATES[sel].dsn;
        if (!dsn) return Promise.resolve();
        return fetch(ACTION_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
            body: JSON.stringify({ dsn, action, value }),
        })
            .then(r => r.json().then(d => ({ ok: r.ok, d })))
            .then(({ ok, d }) => {
                if (ok && d && d.fireplace) {
                    // reconcile cached record from authoritative response (by dsn)
                    const idx = STATES.findIndex(s => s.dsn === d.fireplace.dsn);
                    if (idx >= 0) STATES[idx] = d.fireplace;
                    // refresh visuals only — don't rebuild markup / close the popover
                    if (idx === sel) applyVisual();
                } else if (!ok) {
                    console.error('fireplace action failed', action, d);
                }
            })
            .catch(err => console.error('fireplace action error', action, err));
    }

    function fetchStates() {
        return fetch(STATES_URL)
            .then(r => r.json())
            .then(data => {
                configured = data.configured !== false;
                loadError = data.error || null;
                const list = Array.isArray(data.fireplaces) ? data.fireplaces : [];
                // keep the user's current selection pinned to its dsn across refreshes
                const curDsn = STATES[sel] && STATES[sel].dsn;
                STATES = list;
                if (curDsn) {
                    const i = STATES.findIndex(s => s.dsn === curDsn);
                    sel = i >= 0 ? i : 0;
                } else {
                    sel = 0;
                }
                renderAll();
            })
            .catch(err => {
                console.error('fireplace states error', err);
                loadError = 'Could not reach the fireplace service.';
                renderAll();
            });
    }

    // ── render ───────────────────────────────────────────────
    function showMessage(html) {
        sels.select.innerHTML = '';
        sels.presets.innerHTML = '';
        sels.preview.className = 'preview-wrap';
        sels.preview.innerHTML = `<div class="fp-msg">${html}</div>`;
    }

    function renderSelect() {
        if (STATES.length <= 1) { sels.select.innerHTML = ''; return; }
        sels.select.innerHTML = STATES.map((raw, i) => {
            const f = toView(raw);
            return `
            <div class="fp-pill ${f.power ? 'on' : ''} ${i === sel ? 'active' : ''}" data-sel="${i}">
                <div class="pill-ic"><i class="fa-solid fa-fire"></i></div>
                <div class="pill-txt"><b>${f.name}</b>
                    <span><span class="dot ${f.online ? 'online' : 'offline'}">●</span>${statusText(f)}</span></div>
            </div>`;
        }).join('');
        sels.select.querySelectorAll('[data-sel]').forEach(el => el.onclick = () => {
            sel = +el.dataset.sel; openPop = null; renderAll();
        });
    }

    function applyVisual() {
        const f = view();
        const p = sels.preview;
        p.classList.toggle('on', f.power); p.classList.toggle('off', !f.power);
        p.style.setProperty('--flame-h', (0.15 + f.flame_speed * 0.07).toFixed(2));
        p.style.setProperty('--flame-c1', '#ff7a18');
        p.style.setProperty('--flame-c2', f.yellow_flame >= f.orange_flame ? '#ffe066' : '#ffb030');
        p.style.setProperty('--ember-color', f.ember_rgb);
        p.style.setProperty('--ember-bri', (f.ember_bri / 4).toFixed(2));
        p.style.setProperty('--top-color', f.top_rgb);
        const eb = p.querySelector('.ember-bed'); if (eb) eb.classList.toggle('cycle', f.ember_cycle);
        const tg = p.querySelector('.top-glow'); if (tg) tg.classList.toggle('lit', f.top_on);
        const st = p.querySelector('.pt-status');
        if (st) st.innerHTML = `<span class="dot ${f.online ? 'online' : 'offline'}">●</span> ${statusText(f)}`;
    }

    function emberSpans() {
        let s = '';
        for (let i = 0; i < 55; i++) {
            const left = (2 + Math.random() * 96).toFixed(1);
            const dur = (2.2 + Math.random() * 3.6).toFixed(2);
            const delay = (-Math.random() * 6).toFixed(2);
            const rh = -(120 + Math.random() * 170).toFixed(0);
            const rx = (Math.random() * 60 - 30).toFixed(0);
            const sz = (1.5 + Math.random() * 7).toFixed(1);
            const op = (0.6 + Math.random() * 0.4).toFixed(2);
            s += `<span class="ember" style="left:${left}%; width:${sz}px; height:${sz}px; --op:${op}; animation-duration:${dur}s; animation-delay:${delay}s; --rh:${rh}px; --rx:${rx}px;"></span>`;
        }
        return s;
    }

    const FLAMES = '<div class="flame f3"></div><div class="flame"></div><div class="flame f2"></div><div class="flame"></div><div class="flame f3"></div><div class="flame core"></div><div class="flame f2"></div><div class="flame"></div><div class="flame f3"></div><div class="flame"></div><div class="flame core"></div><div class="flame"></div><div class="flame f3"></div><div class="flame"></div><div class="flame f2"></div><div class="flame core"></div><div class="flame f3"></div><div class="flame"></div><div class="flame f2"></div><div class="flame"></div><div class="flame f3"></div>';

    function renderPreview() {
        const f = view();
        const p = sels.preview;
        p.innerHTML = `
        <div class="preview-top">
            <div class="pt-name">${f.name}</div>
            <div class="pt-status"></div>
        </div>
        <div class="firebox">
            <div class="top-glow"></div>
            <div class="ember-bed"></div>
            <div class="logs"><div class="log l1"></div><div class="log l2"></div><div class="log l3"></div></div>
            <div class="flames">${FLAMES}</div>
            <div class="embers">${emberSpans()}</div>
            <div class="off-overlay"><i class="fa-regular fa-snowflake"></i> ${f.online ? 'Fireplace is off — tap power' : 'Offline'}</div>

            <!-- HEAT -->
            <div class="hotspot below heat ${openPop === 'heat' ? 'open' : ''}" data-hs="heat" style="top:10px; left:13%;">
                <button class="puck" data-puck="heat"><i class="fa-solid fa-temperature-half"></i><span class="plabel">Heat</span></button>
                <div class="pop"><h4><i class="fa-solid fa-temperature-half"></i> Heat</h4>
                    <div class="row"><span class="rl">Heater</span><div class="seg">${HEATER.map((h, hi) => `<button class="${f.heater === hi ? 'active' : ''}" data-heater="${hi}">${h}</button>`).join('')}</div></div>
                    <div class="row"><span class="rl">Target</span><div class="stepper"><button data-temp="-1"><i class="fa-solid fa-minus"></i></button><span class="tv">${f.setpoint_c}°C</span><button data-temp="1"><i class="fa-solid fa-plus"></i></button></div></div>
                    <div class="mini-row"><span class="rl">Eco Mode</span><label class="fp-toggle"><input type="checkbox" ${f.eco ? 'checked' : ''} data-flag="eco"><span class="tt"></span></label></div>
                    <div class="mini-row"><span class="rl">Boost Mode</span><label class="fp-toggle"><input type="checkbox" ${f.boost ? 'checked' : ''} data-flag="boost"><span class="tt"></span></label></div>
                </div>
            </div>

            <!-- TOP LIGHT -->
            <div class="hotspot below ${openPop === 'top' ? 'open' : ''}" data-hs="top" style="top:10px; left:50%;">
                <button class="puck" data-puck="top"><i class="fa-solid fa-lightbulb"></i><span class="plabel">Top Light</span></button>
                <div class="pop"><h4><i class="fa-solid fa-lightbulb"></i> Top Light</h4>
                    <div class="row"><span class="rl">Color</span><input type="color" class="swatch" value="${f.top_rgb}" data-color="top_rgb"></div>
                    <div class="mini-row"><span class="rl">On</span><label class="fp-toggle"><input type="checkbox" ${f.top_on ? 'checked' : ''} data-flag="top_on"><span class="tt"></span></label></div>
                    <div class="mini-row"><span class="rl">Color Cycle</span><label class="fp-toggle"><input type="checkbox" ${f.top_cycle ? 'checked' : ''} data-flag="top_cycle"><span class="tt"></span></label></div>
                </div>
            </div>

            <!-- FLAME -->
            <div class="hotspot below ${openPop === 'flame' ? 'open' : ''}" data-hs="flame" style="top:42%; left:50%;">
                <button class="puck" data-puck="flame"><i class="fa-solid fa-fire-flame-curved"></i><span class="plabel">Flame</span></button>
                <div class="pop"><h4><i class="fa-solid fa-fire-flame-curved"></i> Flame</h4>
                    <div class="row"><span class="rl">Height</span><input type="range" class="sld flamesld" min="1" max="5" value="${f.flame_speed}" data-set="flame_speed"><span class="rv">${f.flame_speed}/5</span></div>
                    <div class="row"><span class="rl">Orange</span><input type="range" class="sld flamesld" min="0" max="4" value="${f.orange_flame}" data-set="orange_flame"><span class="rv">${f.orange_flame}/4</span></div>
                    <div class="row"><span class="rl">Yellow</span><input type="range" class="sld flamesld" min="0" max="4" value="${f.yellow_flame}" data-set="yellow_flame"><span class="rv">${f.yellow_flame}/4</span></div>
                </div>
            </div>

            <!-- EMBER BED -->
            <div class="hotspot above ${openPop === 'ember' ? 'open' : ''}" data-hs="ember" style="bottom:14px; left:50%;">
                <button class="puck" data-puck="ember"><i class="fa-solid fa-fire"></i><span class="plabel">Ember Bed</span></button>
                <div class="pop"><h4><i class="fa-solid fa-fire"></i> Ember Bed</h4>
                    <div class="row"><span class="rl">Color</span><input type="color" class="swatch" value="${f.ember_rgb}" data-color="ember_rgb"></div>
                    <div class="row"><span class="rl">Bright</span><input type="range" class="sld" min="0" max="4" value="${f.ember_bri}" data-set="ember_bri"><span class="rv">${f.ember_bri}/4</span></div>
                    <div class="mini-row"><span class="rl">Color Cycle</span><label class="fp-toggle"><input type="checkbox" ${f.ember_cycle ? 'checked' : ''} data-flag="ember_cycle"><span class="tt"></span></label></div>
                </div>
            </div>

            <!-- POWER -->
            <div class="hotspot power" data-hs="power" style="top:12px; right:12px;">
                <button class="puck" data-puck="power" ${f.online ? '' : 'disabled'}><i class="fa-solid fa-power-off"></i><span class="plabel">${f.power ? 'Turn Off' : 'Turn On'}</span></button>
            </div>
        </div>`;
        wirePreview();
        applyVisual();
    }

    function wirePreview() {
        const p = sels.preview;
        const raw = () => STATES[sel];

        p.querySelectorAll('[data-puck]').forEach(b => b.onclick = (e) => {
            e.stopPropagation();
            const k = b.dataset.puck;
            const f = view();
            if (k === 'power') {
                if (!f.online) return;
                const next = !f.power;
                raw().power = next;
                openPop = null;
                renderAll();
                sendAction('power', next);
                return;
            }
            openPop = (openPop === k) ? null : k;
            renderPreview();
        });

        // sliders / steppers (continuous): update locally, debounce the POST
        p.querySelectorAll('[data-set]').forEach(el => {
            el.addEventListener('pointerdown', () => { editing = true; });
            el.addEventListener('touchstart', () => { editing = true; }, { passive: true });
            el.oninput = () => {
                const key = el.dataset.set;
                const val = +el.value;
                raw()[RAW_FIELD[key]] = val;
                el.parentElement.querySelector('.rv').textContent =
                    el.value + (key === 'flame_speed' ? '/5' : '/4');
                applyVisual();
                debounce(key, () => sendAction(SET_ACTION[key], val));
            };
            const stop = () => { editing = false; };
            el.addEventListener('pointerup', stop);
            el.addEventListener('touchend', stop);
            el.addEventListener('change', stop);
        });

        // boolean flags
        p.querySelectorAll('[data-flag]').forEach(el => el.onchange = () => {
            const flag = el.dataset.flag;
            const checked = el.checked;
            if (flag === 'top_on') {
                // no dedicated setter: derive on/off from rgb (white when on, black when off)
                const rgb = checked ? [255, 255, 255] : [0, 0, 0];
                raw().top_light_rgb = rgb;
                applyVisual();
                sendAction('top_light_rgb', rgb);
                return;
            }
            raw()[RAW_FIELD[flag]] = checked;
            applyVisual();
            sendAction(FLAG_ACTION[flag], checked);
        });

        // color pickers
        p.querySelectorAll('[data-color]').forEach(el => {
            el.addEventListener('pointerdown', () => { editing = true; });
            el.oninput = () => {
                const key = el.dataset.color;
                const rgb = hexToRgbArr(el.value);
                raw()[RAW_FIELD[key]] = rgb;
                applyVisual();
                debounce(key, () => sendAction(COLOR_ACTION[key], rgb));
            };
            el.addEventListener('change', () => { editing = false; });
        });

        // heater segmented
        p.querySelectorAll('[data-heater]').forEach(el => el.onclick = (e) => {
            e.stopPropagation();
            const hi = +el.dataset.heater;
            raw().heater = hi;
            renderPreview();
            sendAction('heater', hi);
        });

        // temperature stepper
        p.querySelectorAll('[data-temp]').forEach(el => el.onclick = (e) => {
            e.stopPropagation();
            const f = view();
            const next = clamp(f.setpoint_c + (+el.dataset.temp), 18, 30);
            raw().setpoint_c = next;
            renderPreview();
            sendAction('setpoint_c', next);
        });

        // keep popover open when interacting inside it
        p.querySelectorAll('.pop').forEach(pop => pop.onclick = e => e.stopPropagation());
    }

    function renderPresets() {
        const f = view();
        const dis = f.power ? '' : 'disabled';
        sels.presets.innerHTML = `
        <div class="ctl ${dis}"><h3><i class="fa-solid fa-wand-magic-sparkles"></i> Presets / Moods</h3>
            <div class="presets">${PRESETS.map(pr => `<button class="preset ${f.favourite === pr.slot ? 'active' : ''}" data-preset="${pr.slot}"><i class="fa-solid ${pr.icon}"></i>${pr.name}</button>`).join('')}</div>
        </div>`;
        sels.presets.querySelectorAll('[data-preset]').forEach(el => el.onclick = () => {
            const slot = el.dataset.preset;
            STATES[sel].current_favourite = slot;
            renderAll();
            sendAction('favourite', slot);
        });
    }

    function renderAll() {
        if (!configured) {
            showMessage('<i class="fa-solid fa-circle-info"></i> Fireplace cloud is not configured. Set NAPOLEON_EMAIL and NAPOLEON_PASSWORD on the server.');
            return;
        }
        if (loadError) {
            showMessage(`<i class="fa-solid fa-triangle-exclamation"></i> ${loadError}`);
            return;
        }
        if (!STATES.length) {
            showMessage('<i class="fa-solid fa-fire"></i> No fireplaces found on this account.');
            return;
        }
        renderSelect();
        renderPreview();
        renderPresets();
    }

    // ── debounce for continuous controls ─────────────────────
    const debTimers = {};
    function debounce(key, fn) {
        if (debTimers[key]) clearTimeout(debTimers[key]);
        debTimers[key] = setTimeout(fn, 350);
    }

    // ── body click closes popover (only on the active fireplace tab) ─
    document.body.addEventListener('click', () => {
        if (!ROOT.classList.contains('active')) return;
        if (openPop) { openPop = null; renderPreview(); }
    });

    // ── poll — skip while a popover is open or a control is being dragged ─
    function poll() {
        if (openPop || editing) return;
        fetchStates();
    }

    // initial load + 9s refresh
    showMessage('<i class="fa-solid fa-spinner fa-spin"></i> Loading fireplace…');
    fetchStates();
    setInterval(poll, 9000);
})();

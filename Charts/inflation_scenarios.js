// =============================================================================
//%% Fixed-coefficient VAR recursion, shared by the browser and numerical checks
function projectScenario(model, paths = {}) {
  const rows = model.seed.map(row => row.slice());
  const levels = model.cpiHistory.slice();
  const rates = [];
  const yoy = model.dates.map((date, h) => {
    const next = model.intercept.slice();
    model.coefficients.forEach((matrix, lag) => {
      const previous = rows[rows.length - lag - 1];
      matrix.forEach((equation, i) => equation.forEach((weight, j) => { next[i] += weight * previous[j]; }));
    });
    Object.entries(paths).forEach(([name, values]) => {
      const driver = model.drivers[name], value = values[h];
      if (!driver || !Number.isFinite(value) ||
          (driver.minimum !== null && value < driver.minimum) ||
          (driver.maximum !== null && value > driver.maximum)) {
        throw new Error(`Invalid ${name} path value.`);
      }
      next[driver.index] = value;
    });
    if (!next.every(Number.isFinite) || next[0] <= -100) throw new Error('This path produces invalid inflation levels. Try a smaller change.');
    rows.push(next);
    rates.push(next);
    const level = levels[levels.length - 1] * (1 + next[0] / 100);
    const result = 100 * (level / levels[levels.length - model.year] - 1);
    if (!Number.isFinite(result)) throw new Error('This path produces an invalid forecast. Try a smaller change.');
    levels.push(level);
    return result;
  });
  return {yoy, rates};
}

// =============================================================================
//%% Shared driver edits: active paths combine in a single recursion
function projectOilScenario(model, oilPath) {
  return projectScenario(model, {oil: oilPath});
}

function projectCountryScenario(models, edits) {
  return models.map(model => {
    const paths = {};
    edits.forEach((values, name) => {
      if (!values.size || !model.drivers[name]) return;
      paths[name] = model.dates.map((date, i) => values.has(date) ? values.get(date) : model.drivers[name].baseline[i]);
    });
    return projectScenario(model, paths);
  });
}

// =============================================================================
//%% Sample a freehand stroke at forecast dates, including skipped points
function sampleOilStroke(positions, start, end) {
  const nearest = x => positions.reduce((best, value, i) =>
    Math.abs(value - x) < Math.abs(positions[best] - x) ? i : best, 0);
  const first = nearest(start.x), last = nearest(end.x);
  const samples = [];
  for (let i = Math.min(first, last); i <= Math.max(first, last); i++) {
    const fraction = end.x === start.x ? 1 : Math.max(0, Math.min(1, (positions[i] - start.x) / (end.x - start.x)));
    samples.push([i, start.y + fraction * (end.y - start.y)]);
  }
  return samples;
}

// =============================================================================
//%% Freehand driver drawing and synchronized inflation charts
async function initializeOilScenarios() {
  const countries = new Map();
  const editors = Array.from(document.querySelectorAll('.oil-scenario')).map(root => {
    const country = root.dataset.country;
    if (!countries.has(country)) countries.set(country, new Map());
    const models = JSON.parse(root.querySelector('.scenario-data').textContent);
    const edits = countries.get(country);
    Object.keys(models[0].drivers).forEach(name => { if (!edits.has(name)) edits.set(name, new Map()); });
    return {root, country, models, edits, views: [], results: projectCountryScenario(models, edits)};
  });
  function updateCountry(country) {
    const peers = editors.filter(editor => editor.country === country);
    const results = peers.map(editor => projectCountryScenario(editor.models, editor.edits));
    peers.forEach((editor, i) => {
      editor.results = results[i];
      if (editor.render) editor.render();
    });
  }
  for (const editor of editors) {
    const {root, models, edits, country} = editor, model = models[0];
    const status = root.querySelector('[data-role="status"]');
    const inflation = document.getElementById(`${root.id}-inflation`);
    editor.render = () => {
      Plotly.restyle(inflation, {
        x: models.map(m => [m.lastDate, ...m.dates]),
        y: models.map((m, i) => [m.lastYoy, ...editor.results[i].yoy]),
      }, models.map((m, i) => 2 * i + 1));
      editor.views.forEach(view => view.render());
      const active = [...edits].filter(([name, values]) => values.size).map(([name]) => model.drivers[name].label);
      const impacts = models.map((m, i) => {
        const peak = editor.results[i].yoy.reduce((best, value, h) => Math.abs(value - m.baselineYoy[h]) > Math.abs(best) ? value - m.baselineYoy[h] : best, 0);
        return `${m.label}: ${Math.abs(peak) < 0.0005 ? '0.000' : (peak > 0 ? '+' : '') + peak.toFixed(3)} pp`;
      });
      status.textContent = active.length
        ? `Active: ${active.join(', ')}. Largest changes vs original: ${impacts.join('; ')}. Effects enter through lags.`
        : 'Original forecasts. Draw in any shaded chart to combine driver paths.';
    };
    for (const card of root.querySelectorAll('.driver-card')) {
      const name = card.dataset.driver, driver = model.drivers[name], values = edits.get(name);
      const chart = document.getElementById(`${root.id}-${name}`);
      const overlay = card.querySelector('.oil-drag-handles');
      const period = card.querySelector('[data-role="period"]'), input = card.querySelector('[data-role="price"]');
      const path = () => editor.results[0].rates.map(row => row[driver.index]);
      const clamp = value => Math.max(driver.minimum ?? -Infinity, Math.min(driver.maximum ?? Infinity, value));
      let stroke = null;
      function chartRange() {
        const all = [...driver.history.slice(-model.year * 2), ...driver.baseline, ...path()];
        const low = Math.min(...all), high = Math.max(...all), pad = Math.max((high - low) * 0.5, name === 'oil' ? 30 : 2);
        return [clamp(low - pad), clamp(high + pad)];
      }
      period.replaceChildren(...model.periods.map((label, i) => new Option(label, i)));
      if (driver.minimum !== null) input.min = driver.minimum;
      if (driver.maximum !== null) input.max = driver.maximum;
      function select(index) { period.value = String(index); input.value = path()[index].toFixed(2); }
      await Plotly.newPlot(chart, [
        {x: driver.dates, y: driver.history, name: 'Observed', mode: 'lines', line: {color: '#0B6E4F', width: 2}},
        {x: [model.lastDate, ...model.dates], y: [driver.last, ...driver.baseline], name: 'Original forecast', mode: 'lines', line: {color: '#9A9A9A', dash: 'dash', width: 1.5}},
        {x: [model.lastDate, ...model.dates], y: [driver.last, ...path()], name: 'Scenario path', mode: 'lines', line: {color: '#B5651D', width: 2}},
      ], {
        height: 280, margin: {l: 32, r: 8, t: 10, b: 30}, showlegend: false,
        font: {family: 'Gill Sans MT, Gill Sans, Arial, sans-serif', size: 10, color: '#1A1A1A'},
        paper_bgcolor: 'white', plot_bgcolor: 'white', hovermode: 'closest', dragmode: false,
        xaxis: {type: 'date', fixedrange: true, showgrid: false, nticks: 3, tickformat: '%Y',
          range: [driver.dates[Math.max(0, driver.dates.length - model.year * 2)], model.dates[model.dates.length - 1]]},
        yaxis: {fixedrange: true, range: chartRange(), nticks: 4, gridcolor: '#EFEFEF'},
      }, {responsive: true, displaylogo: false, displayModeBar: false});
      const surface = document.createElement('div');
      surface.className = 'oil-draw-surface';
      surface.setAttribute('aria-label', `Draw ${driver.label.toLowerCase()} across future periods`);
      overlay.appendChild(surface);
      const handles = model.dates.map((date, i) => {
        const handle = document.createElement('button');
        handle.type = 'button'; handle.className = 'oil-handle';
        handle.setAttribute('aria-label', `${driver.label}, ${model.periods[i]}; arrow keys adjust value`);
        handle.addEventListener('keydown', event => {
          if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return;
          event.preventDefault(); select(i);
          change([[i, clamp(path()[i] + (event.key === 'ArrowUp' ? driver.keyStep : -driver.keyStep))]]);
        });
        overlay.appendChild(handle); return handle;
      });
      function positionHandles() {
        const {xaxis, yaxis} = chart._fullLayout, left = Math.max(0, xaxis.d2p(model.lastDate));
        Object.assign(surface.style, {left: `${xaxis._offset + left}px`, top: `${yaxis._offset}px`,
          width: `${xaxis._length - left}px`, height: `${yaxis._length}px`});
        path().forEach((value, i) => {
          handles[i].style.left = `${xaxis._offset + xaxis.d2p(model.dates[i])}px`;
          handles[i].style.top = `${yaxis._offset + yaxis.d2p(value)}px`;
          handles[i].title = `${model.periods[i]}: ${value.toFixed(2)} ${driver.unit}`;
        });
      }
      chart.on('plotly_afterplot', positionHandles);
      const view = {render() {
        // Anchor the scenario to the actual observation, including after edits/reset.
        Plotly.restyle(chart, {y: [[driver.last, ...path()]]}, [2]);
        if (!stroke && path().some(value => value < chart._fullLayout.yaxis.range[0] || value > chart._fullLayout.yaxis.range[1])) {
          Plotly.relayout(chart, {'yaxis.range': chartRange()});
        }
        positionHandles(); select(Number(period.value));
      }};
      editor.views.push(view);
      function change(samples) {
        const previous = new Map(values);
        for (const [i, value] of samples) {
          if (!Number.isFinite(value) || value !== clamp(value)) return;
        }
        samples.forEach(([i, value]) => values.set(model.dates[i], value));
        try { updateCountry(country); }
        catch (error) {
          values.clear(); previous.forEach((value, date) => values.set(date, value));
          status.textContent = error.message;
        }
      }
      function pointerPosition(event) {
        const box = chart.getBoundingClientRect(), {xaxis, yaxis} = chart._fullLayout;
        return {x: Math.max(0, Math.min(xaxis._length, event.clientX - box.left - xaxis._offset)),
          y: Math.max(0, Math.min(yaxis._length, event.clientY - box.top - yaxis._offset))};
      }
      function draw(event) {
        if (!stroke || event.pointerId !== stroke.id) return;
        const end = pointerPosition(event), {xaxis, yaxis} = chart._fullLayout;
        change(sampleOilStroke(model.dates.map(date => xaxis.d2p(date)), stroke.point, end)
          .map(([i, y]) => [i, clamp(yaxis.p2d(y))]));
        stroke.point = end;
      }
      surface.addEventListener('pointerdown', event => {
        if (event.button !== 0 || stroke) return;
        event.preventDefault(); stroke = {id: event.pointerId, point: pointerPosition(event)};
        surface.setPointerCapture(event.pointerId); draw(event);
      });
      surface.addEventListener('pointermove', draw);
      surface.addEventListener('pointerup', event => { draw(event); if (stroke?.id === event.pointerId) stroke = null; });
      surface.addEventListener('pointercancel', () => { stroke = null; });
      surface.addEventListener('lostpointercapture', () => { stroke = null; });
      period.addEventListener('change', () => select(Number(period.value)));
      const apply = () => { if (input.reportValidity()) change([[Number(period.value), Number(input.value)]]); };
      card.querySelector('[data-role="apply"]').addEventListener('click', apply);
      input.addEventListener('change', apply);
      input.addEventListener('keydown', event => { if (event.key === 'Enter') apply(); });
      card.querySelector('[data-role="reset-driver"]').addEventListener('click', () => { values.clear(); updateCountry(country); });
      view.render();
    }
    root.querySelector('[data-role="reset"]').addEventListener('click', () => { edits.forEach(values => values.clear()); updateCountry(country); });
    editor.render();
  }
}

if (typeof document !== 'undefined') initializeOilScenarios();
if (typeof module !== 'undefined') module.exports = {projectScenario, projectOilScenario, projectCountryScenario, sampleOilStroke};

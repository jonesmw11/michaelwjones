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
    return {root, country, models: JSON.parse(root.querySelector('.scenario-data').textContent)};
  });
  for (const editor of editors) {
    const {root, models, country} = editor, m = models[0];
    const countryEdits = countries.get(country);
    Object.keys(m.drivers).forEach(name => { if (!countryEdits.has(name)) countryEdits.set(name, new Map()); });
    let active = 'oil';
    const driver = () => m.drivers[active];
    const edits = () => countryEdits.get(active);
    const find = role => root.querySelector(`[data-role="${role}"]`);
    const period = find('period'), price = find('price'), status = find('status'), driverSelect = find('driver');
    const inflation = document.getElementById(`${root.id}-inflation`);
    const oil = document.getElementById(`${root.id}-oil`);
    const overlay = root.querySelector('.oil-drag-handles');
    let currentResults = projectCountryScenario(models, countryEdits);
    const path = () => currentResults[0].rates.map(row => row[driver().index]);
    const clamp = value => Math.max(driver().minimum ?? -Infinity, Math.min(driver().maximum ?? Infinity, value));
    function chartRange() {
      const values = [...driver().history.slice(-m.year * 2), ...path(), ...driver().baseline];
      const low = Math.min(...values), high = Math.max(...values);
      const pad = Math.max((high - low) * 0.5, active === 'oil' ? 30 : 2);
      return [clamp(low - pad), clamp(high + pad)];
    }
    const signed = value => Math.abs(value) < 0.0005 ? '0.000' : `${value > 0 ? '+' : ''}${value.toFixed(3)}`;
    period.replaceChildren(...m.periods.map((label, i) => new Option(`${label} · +${i + 1}`, i)));
    function select(index) {
      period.value = String(index);
      price.value = path()[index].toFixed(2);
    }
    const layout = {
      height: 420, margin: {l: 55, r: 18, t: 70, b: 40},
      font: {family: 'Gill Sans MT, Gill Sans, Arial, sans-serif', color: '#1A1A1A'},
      paper_bgcolor: 'white', plot_bgcolor: 'white', hovermode: 'closest', dragmode: false,
      legend: {orientation: 'h', y: 1.03, yanchor: 'bottom', x: 0, xanchor: 'left', font: {size: 11}},
      xaxis: {type: 'date', showgrid: false, fixedrange: true,
        range: [driver().dates[Math.max(0, driver().dates.length - m.year * 2)], m.dates[m.dates.length - 1]]},
      yaxis: {title: {text: driver().unit}, gridcolor: '#EFEFEF', fixedrange: true,
        range: chartRange()},
    };
    await Plotly.newPlot(oil, [
      {x: driver().dates, y: driver().history, name: 'Observed', mode: 'lines', line: {color: '#0B6E4F'}},
      {x: [m.lastDate, ...m.dates], y: [driver().last, ...driver().baseline], name: 'Original forecast', mode: 'lines', line: {color: '#9A9A9A', dash: 'dash'}},
      {x: m.dates, y: path(), name: 'Scenario path', mode: 'lines', line: {color: '#B5651D', width: 2.5}},
    ], layout, {responsive: true, displaylogo: false, displayModeBar: false});
    const surface = document.createElement('div');
    surface.className = 'oil-draw-surface';
    surface.setAttribute('aria-label', 'Draw the selected driver path across future periods');
    overlay.appendChild(surface);
    const handles = m.dates.map((date, i) => {
      const handle = document.createElement('button');
      handle.type = 'button';
      handle.className = 'oil-handle';
      handle.setAttribute('aria-label', `Driver value for ${m.periods[i]}; use arrow keys to adjust`);
      handle.addEventListener('keydown', event => {
        if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return;
        event.preventDefault();
        select(i);
        change(i, clamp(path()[i] + (event.key === 'ArrowUp' ? driver().keyStep : -driver().keyStep)));
      });
      overlay.appendChild(handle);
      return handle;
    });
    function positionHandles() {
      const {xaxis, yaxis} = oil._fullLayout;
      const left = Math.max(0, xaxis.d2p(m.lastDate));
      Object.assign(surface.style, {left: `${xaxis._offset + left}px`, top: `${yaxis._offset}px`,
        width: `${xaxis._length - left}px`, height: `${yaxis._length}px`});
      path().forEach((value, i) => {
        handles[i].style.left = `${xaxis._offset + xaxis.d2p(m.dates[i])}px`;
        handles[i].style.top = `${yaxis._offset + yaxis.d2p(value)}px`;
        handles[i].title = `${driver().label}, ${m.periods[i]}: ${value.toFixed(2)} ${driver().unit}`;
      });
    }
    oil.on('plotly_afterplot', positionHandles);
    editor.render = function(results) {
      currentResults = results;
      Plotly.restyle(inflation, {
        x: models.map(model => [model.lastDate, ...model.dates]),
        y: models.map((model, i) => [model.lastYoy, ...results[i].yoy]),
      }, models.map((model, i) => 2 * i + 1));
      Plotly.restyle(oil, {y: [path()]}, [2]);
      if (!stroke && path().some(value => value < oil._fullLayout.yaxis.range[0] || value > oil._fullLayout.yaxis.range[1])) {
        Plotly.relayout(oil, {'yaxis.range': chartRange()});
      }
      positionHandles();
      const impacts = models.map((model, i) => {
        const peak = results[i].yoy.reduce((best, value, h) =>
          Math.abs(value - model.baselineYoy[h]) > Math.abs(best) ? value - model.baselineYoy[h] : best, 0);
        return `${model.label}: ${signed(peak)} pp`;
      });
      const activeNames = [...countryEdits].filter(([name, values]) => values.size).map(([name]) => m.drivers[name]?.label ?? name);
      status.textContent = activeNames.length
        ? `Active: ${activeNames.join(", ")}. Largest changes vs original: ${impacts.join('; ')}. Effects start after the model's lag, not in the edited period itself.`
        : 'Original forecasts. Press anywhere in the shaded forecast area and draw across it to update all measures.';
      select(Number(period.value));
    };
    function updateCountry() {
      const peers = editors.filter(item => item.country === country);
      // Validate every result before updating any of the charts.
      const results = peers.map(item => projectCountryScenario(item.models, countryEdits));
      peers.forEach((item, i) => { if (item.render) item.render(results[i]); });
    }
    function change(index, value) {
      const date = m.dates[index], previous = edits().get(date);
      if (!Number.isFinite(value) || value !== clamp(value)) return;
      edits().set(date, value);
      try { updateCountry(); }
      catch (error) {
        if (previous === undefined) edits().delete(date); else edits().set(date, previous);
        status.textContent = error.message;
      }
    }
    let stroke = null;
    function pointerPosition(event) {
      const box = oil.getBoundingClientRect(), {xaxis, yaxis} = oil._fullLayout;
      return {x: Math.max(0, Math.min(xaxis._length, event.clientX - box.left - xaxis._offset)),
        y: Math.max(0, Math.min(yaxis._length, event.clientY - box.top - yaxis._offset))};
    }
    function draw(event) {
      if (!stroke || event.pointerId !== stroke.id) return;
      const end = pointerPosition(event), {xaxis, yaxis} = oil._fullLayout;
      const samples = sampleOilStroke(m.dates.map(date => xaxis.d2p(date)), stroke.point, end);
      const previous = new Map(edits());
      samples.forEach(([i, y]) => edits().set(m.dates[i], clamp(yaxis.p2d(y))));
      try { updateCountry(); }
      catch (error) {
        edits().clear(); previous.forEach((value, date) => edits().set(date, value));
        status.textContent = error.message;
      }
      stroke.point = end;
    }
    surface.addEventListener('pointerdown', event => {
      if (event.button !== 0 || stroke) return;
      event.preventDefault();
      stroke = {id: event.pointerId, point: pointerPosition(event)};
      surface.setPointerCapture(event.pointerId);
      draw(event);
    });
    surface.addEventListener('pointermove', draw);
    surface.addEventListener('pointerup', event => {
      draw(event);
      if (stroke && event.pointerId === stroke.id) stroke = null;
    });
    surface.addEventListener('pointercancel', () => { stroke = null; });
    surface.addEventListener('lostpointercapture', () => { stroke = null; });
    period.addEventListener('change', () => select(Number(period.value)));
    function apply() { if (price.reportValidity()) change(Number(period.value), Number(price.value)); }
    find('apply').addEventListener('click', apply);
    price.addEventListener('change', apply);
    price.addEventListener('keydown', event => { if (event.key === 'Enter') apply(); });
    find('reset').addEventListener('click', () => { countryEdits.forEach(values => values.clear()); updateCountry(); });
    find('reset-driver').addEventListener('click', () => { edits().clear(); updateCountry(); });
    price.required = true;
    driverSelect.addEventListener('change', async () => {
      stroke = null;
      active = driverSelect.value;
      const d = driver();
      find('value-label').textContent = `${d.label} (${d.unit})`;
      if (d.minimum === null) price.removeAttribute('min'); else price.min = d.minimum;
      if (d.maximum === null) price.removeAttribute('max'); else price.max = d.maximum;
      await Plotly.restyle(oil, {x: [d.dates, [m.lastDate, ...m.dates], m.dates],
        y: [d.history, [d.last, ...d.baseline], path()]});
      await Plotly.relayout(oil, {'yaxis.title.text': d.unit, 'yaxis.range': chartRange()});
      positionHandles();
      select(Number(period.value));
    });
    editor.render(projectCountryScenario(models, countryEdits));
  }
}

if (typeof document !== 'undefined') initializeOilScenarios();
if (typeof module !== 'undefined') module.exports = {projectScenario, projectOilScenario, projectCountryScenario, sampleOilStroke};

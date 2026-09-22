// =============================================================================
//%% Fixed-coefficient VAR recursion, shared by the browser and numerical checks
function projectOilScenario(model, oilPath) {
  const rows = model.seed.map(row => row.slice());
  const levels = model.cpiHistory.slice();
  const rates = [];
  let previousOil = model.oilLast;
  const yoy = oilPath.map(price => {
    if (!Number.isFinite(price) || price <= 0) throw new Error('Enter a positive oil price.');
    const next = model.intercept.slice();
    model.coefficients.forEach((matrix, lag) => {
      const previous = rows[rows.length - lag - 1];
      matrix.forEach((equation, i) => equation.forEach((weight, j) => { next[i] += weight * previous[j]; }));
    });
    next[model.oilIndex] = 100 * (price / previousOil - 1);
    previousOil = price;
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
//%% Shared country edits: untouched dates preserve each fitted baseline
function projectCountryScenario(models, edits) {
  return models.map(model => projectOilScenario(model,
    model.dates.map((date, i) => edits.has(date) ? edits.get(date) : model.oilBaseline[i])));
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
//%% Freehand oil drawing and synchronized inflation charts
async function initializeOilScenarios() {
  const countries = new Map();
  const editors = Array.from(document.querySelectorAll('.oil-scenario')).map(root => {
    const country = root.dataset.country;
    if (!countries.has(country)) countries.set(country, new Map());
    return {root, country, models: JSON.parse(root.querySelector('.scenario-data').textContent)};
  });
  for (const editor of editors) {
    const {root, models, country} = editor, m = models[0];
    const edits = countries.get(country);
    const find = role => root.querySelector(`[data-role="${role}"]`);
    const period = find('period'), price = find('price'), status = find('status');
    const inflation = document.getElementById(`${root.id}-inflation`);
    const oil = document.getElementById(`${root.id}-oil`);
    const overlay = root.querySelector('.oil-drag-handles');
    const path = () => m.dates.map((date, i) => edits.has(date) ? edits.get(date) : m.oilBaseline[i]);
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
        range: [m.oilDates[Math.max(0, m.oilDates.length - m.year * 2)], m.dates[m.dates.length - 1]]},
      yaxis: {title: {text: 'USD per barrel'}, gridcolor: '#EFEFEF', fixedrange: true,
        range: [0, Math.max(...m.oilHistory.slice(-m.year * 2), ...m.oilBaseline) * 1.6]},
    };
    await Plotly.newPlot(oil, [
      {x: m.oilDates, y: m.oilHistory, name: 'Observed oil', mode: 'lines', line: {color: '#0B6E4F'}},
      {x: [m.lastDate, ...m.dates], y: [m.oilLast, ...m.oilBaseline], name: 'Original oil forecast', mode: 'lines', line: {color: '#9A9A9A', dash: 'dash'}},
      {x: m.dates, y: path(), name: 'Draw your oil path', mode: 'lines', line: {color: '#B5651D', width: 2.5}},
    ], layout, {responsive: true, displaylogo: false, displayModeBar: false});
    const surface = document.createElement('div');
    surface.className = 'oil-draw-surface';
    surface.setAttribute('aria-label', 'Draw an oil price path across future periods');
    overlay.appendChild(surface);
    const handles = m.dates.map((date, i) => {
      const handle = document.createElement('button');
      handle.type = 'button';
      handle.className = 'oil-handle';
      handle.setAttribute('aria-label', `Oil price for ${m.periods[i]}; arrow keys adjust by one dollar`);
      handle.addEventListener('keydown', event => {
        if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return;
        event.preventDefault();
        select(i);
        change(i, Math.max(0.01, path()[i] + (event.key === 'ArrowUp' ? 1 : -1)));
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
        handles[i].title = `${m.periods[i]}: $${value.toFixed(2)}`;
      });
    }
    oil.on('plotly_afterplot', positionHandles);
    editor.render = function(results) {
      Plotly.restyle(inflation, {
        x: models.map(model => [model.lastDate, ...model.dates]),
        y: models.map((model, i) => [model.lastYoy, ...results[i].yoy]),
      }, models.map((model, i) => 2 * i + 1));
      Plotly.restyle(oil, {y: [path()]}, [2]);
      positionHandles();
      const impacts = models.map((model, i) => {
        const peak = results[i].yoy.reduce((best, value, h) =>
          Math.abs(value - model.baselineYoy[h]) > Math.abs(best) ? value - model.baselineYoy[h] : best, 0);
        return `${model.label}: ${signed(peak)} pp`;
      });
      status.textContent = edits.size
        ? `All forecast lines updated. Largest changes vs original: ${impacts.join('; ')}. Effects start after the model's lag, not in the edited period itself.`
        : 'Original forecasts. Press anywhere in the shaded forecast area and draw across it to update all measures.';
      select(Number(period.value));
    };
    function updateCountry() {
      const peers = editors.filter(item => item.country === country);
      // Validate every result before updating any of the charts.
      const results = peers.map(item => projectCountryScenario(item.models, edits));
      peers.forEach((item, i) => { if (item.render) item.render(results[i]); });
    }
    function change(index, value) {
      const date = m.dates[index], previous = edits.get(date);
      if (!Number.isFinite(value) || value <= 0) return;
      edits.set(date, value);
      try { updateCountry(); }
      catch (error) {
        if (previous === undefined) edits.delete(date); else edits.set(date, previous);
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
      const previous = new Map(edits);
      samples.forEach(([i, y]) => edits.set(m.dates[i], Math.max(0.01, yaxis.p2d(y))));
      try { updateCountry(); }
      catch (error) {
        edits.clear(); previous.forEach((value, date) => edits.set(date, value));
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
    find('reset').addEventListener('click', () => { edits.clear(); updateCountry(); });
    price.required = true;
    editor.render(projectCountryScenario(models, edits));
  }
}

if (typeof document !== 'undefined') initializeOilScenarios();
if (typeof module !== 'undefined') module.exports = {projectOilScenario, projectCountryScenario, sampleOilStroke};

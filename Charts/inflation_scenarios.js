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
//%% Clickable oil charts and accessible numeric controls
function initializeOilScenarios() {
  document.querySelectorAll('.oil-scenario').forEach(root => {
    const models = JSON.parse(root.querySelector('.scenario-data').textContent);
    const paths = models.map(model => model.oilBaseline.slice());
    const find = role => root.querySelector(`[data-role="${role}"]`);
    const measure = find('measure'), period = find('period'), price = find('price'), status = find('status');
    const inflation = document.getElementById(`${root.id}-inflation`);
    const oil = document.getElementById(`${root.id}-oil`);
    const scenarioTrace = inflation.data.length - 1;
    let selection = 0;
    const model = () => models[selection];
    const layout = {
      height: 350, margin: {l: 65, r: 24, t: 45, b: 45},
      font: {family: 'Gill Sans MT, Gill Sans, Arial, sans-serif', color: '#1A1A1A'},
      paper_bgcolor: 'white', plot_bgcolor: 'white', hovermode: 'closest',
      legend: {orientation: 'h', y: 1.15},
      xaxis: {type: 'date', showgrid: false}, yaxis: {title: {text: 'USD per barrel'}, gridcolor: '#EFEFEF'},
    };
    function choosePeriod() {
      price.value = paths[selection][Number(period.value)].toFixed(2);
    }
    function redraw() {
      const m = model(), path = paths[selection], result = projectOilScenario(m, path);
      Plotly.restyle(inflation, {
        x: [[m.lastDate, ...m.dates]], y: [[m.lastYoy, ...result.yoy]],
        name: `${m.label}: oil scenario`, hovertemplate: 'Oil scenario: %{y:.2f}%<extra></extra>',
      }, [scenarioTrace]);
      Plotly.react(oil, [
        {x: m.oilDates, y: m.oilHistory, name: 'Observed oil', mode: 'lines', line: {color: '#0B6E4F'}},
        {x: [m.lastDate, ...m.dates], y: [m.oilLast, ...m.oilBaseline], name: 'VAR baseline', mode: 'lines', line: {color: '#9A9A9A', dash: 'dash'}},
        {x: m.dates, y: path, name: 'Editable oil path', mode: 'lines+markers', line: {color: '#B5651D'}, marker: {size: 8},
          hovertemplate: '%{x|%b %Y}: $%{y:.2f}<extra>Click to edit</extra>'},
      ], {...layout, uirevision: String(selection)}, {responsive: true, displaylogo: false});
      const h = Number(period.value);
      const delta = result.yoy[h] - m.baselineYoy[h];
      const peak = result.yoy.reduce((best, value, i) => Math.abs(value - m.baselineYoy[i]) > Math.abs(best) ? value - m.baselineYoy[i] : best, 0);
      status.textContent = `${m.periods[h]}: ${result.yoy[h].toFixed(2)}% inflation (${delta >= 0 ? '+' : ''}${delta.toFixed(2)} pp vs baseline). Largest change over the horizon: ${peak >= 0 ? '+' : ''}${peak.toFixed(2)} pp. VAR(${m.lag}); observed through ${m.lastPeriod}.`;
    }
    function changeMeasure() {
      selection = Number(measure.value);
      period.replaceChildren(...model().periods.map((label, i) => new Option(`${label} · +${i + 1}`, i)));
      choosePeriod();
      redraw();
    }
    function applyPrice() {
      if (!price.reportValidity()) return;
      const value = Number(price.value), h = Number(period.value), old = paths[selection][h];
      paths[selection][h] = value;
      try { redraw(); } catch (error) { paths[selection][h] = old; status.textContent = error.message; }
    }
    measure.addEventListener('change', changeMeasure);
    period.addEventListener('change', () => { choosePeriod(); redraw(); });
    find('apply').addEventListener('click', applyPrice);
    price.addEventListener('keydown', event => { if (event.key === 'Enter') applyPrice(); });
    find('reset').addEventListener('click', () => { paths[selection] = model().oilBaseline.slice(); choosePeriod(); redraw(); });
    price.required = true;
    changeMeasure();
    oil.on('plotly_click', event => {
      const point = event.points.find(item => item.curveNumber === 2);
      if (!point) return;
      period.value = String(point.pointNumber);
      choosePeriod();
      redraw();
      price.focus();
      price.select();
    });
  });
}

if (typeof document !== 'undefined') initializeOilScenarios();
if (typeof module !== 'undefined') module.exports = {projectOilScenario};

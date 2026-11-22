// Phone side of GBD-200: the settings page, sending the choices to the watch,
// and - when the seconds show the temperature - forwarding it from the Pebble
// app's weather plugin (Pebble.subscribeToSource, plugins developer preview).

var keys = require('message_keys');

var STORAGE_KEY = 'gbd200-settings';
var FILL = 0, ORIGINAL = 1, REAL = 2, CUSTOM = 3;
var MIN_PERCENT = 100, MAX_PERCENT = 136, REAL_PERCENT = 110;  // matches src/c/main.c
var SECONDS_OFF = 0, SECONDS_ON = 1, SECONDS_TEMPERATURE = 2;  // matches src/c/main.c
var TZ_DST = 0, TZ_NAME = 1, TZ_OFF = 2;                       // matches src/c/main.c
var PANEL_GRAY = 0, PANEL_INVERTED = 1, PANEL_OFF = 2;         // matches src/c/main.c
var SHADE_SOLID = 0, SHADE_DARKER = 1, SHADE_DARKEST = 2;      // matches src/c/main.c

// Indicators, as a bitmask (matches src/c/main.c).
var INDICATORS = [
  {bit: 1, label: 'SNZ', detail: 'Snooze'},
  {bit: 2, label: 'Alarm signal', detail: 'The speaker icon, shown while you have a Pebble alarm set'},
  {bit: 4, label: 'Button tone off', detail: 'The crossed-out note'},
  {bit: 8, label: 'VIB', detail: 'Vibration'},
  {bit: 16, label: 'LT', detail: 'Auto light'},
  {bit: 256, label: 'Low battery (!)', detail: 'Shown when the Pebble battery is at 20% or less', inverted: true},
  {bit: 512, label: 'Notification bubble', detail: 'Drawn without the count: Pebble watchfaces can\'t read notifications', inverted: true},
  {bit: 64, label: 'Airplane', detail: 'Shown instead of the Bluetooth icons while the phone is disconnected'},
  {bit: 128, label: 'PEBBLE / WR30M', detail: 'Case printing above and below the display (where CASIO and WR20BAR are)', inverted: true},
  {bit: 1024, label: 'Button labels', detail: 'REV, UP and DOWN beside the buttons (and RUN\'s orange triangle by Select), when the display size leaves room', inverted: true}
];
var DEFAULT_INDICATORS = 2 | 4 | 8;

function loadSettings() {
  var s;
  try {
    s = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch (e) {
    s = {};
  }
  // Settings saved before the seconds could show the temperature.
  if (typeof s.SecondsMode !== 'number') s.SecondsMode = s.ShowSeconds === true ? SECONDS_ON : SECONDS_OFF;
  return s;
}

function oneOf(value, allowed, fallback) {
  return allowed.indexOf(value) >= 0 ? value : fallback;
}

function pageHtml(settings) {
  var mode = oneOf(settings.ScaleMode, [FILL, ORIGINAL, REAL, CUSTOM], FILL);
  var pct = typeof settings.ScalePercent === 'number' ? settings.ScalePercent : REAL_PERCENT;
  var secs = oneOf(settings.SecondsMode, [SECONDS_OFF, SECONDS_ON, SECONDS_TEMPERATURE], SECONDS_OFF);
  var tz = oneOf(settings.TzMode, [TZ_DST, TZ_NAME, TZ_OFF], TZ_DST);
  var panel = oneOf(settings.PanelMode, [PANEL_GRAY, PANEL_INVERTED, PANEL_OFF], PANEL_GRAY);
  var shade = oneOf(settings.PanelShade, [SHADE_SOLID, SHADE_DARKER, SHADE_DARKEST], SHADE_DARKER);
  var ind = typeof settings.Indicators === 'number' ? settings.Indicators : DEFAULT_INDICATORS;
  function option(group, current, value, title, detail) {
    return '<label class="opt"><input type="radio" name="' + group + '" value="' + value + '"' +
      (current === value ? ' checked' : '') + '><span><b>' + title + '</b><small>' + detail +
      '</small></span></label>';
  }
  // An inverted item's bit means "hidden", so it is shown by default.
  function check(item) {
    var on = item.inverted ? !(ind & item.bit) : !!(ind & item.bit);
    return '<label class="opt"><input type="checkbox" class="ind' + (item.inverted ? ' inv' : '') +
      '" value="' + item.bit + '"' + (on ? ' checked' : '') + '><span><b>' + item.label + '</b><small>' +
      item.detail + '</small></span></label>';
  }
  return '<!DOCTYPE html><html><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1">' +
    '<title>GBD-200 Settings</title><style>' +
    'body{margin:0;padding:16px;background:#111;color:#eee;font:16px/1.4 -apple-system,Roboto,sans-serif}' +
    'h1{font-size:22px;margin:4px 0 16px}h2{font-size:18px;margin:24px 0 12px}' +
    '.opt{display:flex;gap:12px;align-items:flex-start;padding:14px;margin-bottom:10px;' +
    'background:#222;border-radius:10px}' +
    '*{box-sizing:border-box}' +
    '.opt input[type=radio],.opt input[type=checkbox]{margin-top:4px;transform:scale(1.3)}' +
    '.opt input[type=range]{display:block;width:100%;margin:10px 0 0}' +
    '.opt small{display:block;color:#aaa;font-size:14px;margin-top:2px}' +
    'button{width:100%;padding:14px;font-size:17px;border:0;border-radius:10px;' +
    'background:#ff6a00;color:#fff;margin-top:8px}' +
    '</style></head><body><h1>Display size</h1>' +
    option('mode', mode, FILL, 'Fill width', 'Scaled up 4/3 to fill the screen width, same proportions as the real watch.') +
    option('mode', mode, ORIGINAL, 'Original scale', 'One watch LCD dot per screen pixel, centered on the screen.') +
    option('mode', mode, REAL, 'Real size', 'The same physical size as the real watch (' + REAL_PERCENT +
      '%, matched side by side against a real GBD-200).') +
    option('mode', mode, CUSTOM, 'Custom size', 'Pick your own scale below.') +
    '<div class="opt"><span style="flex:1;min-width:0"><b>Custom size: <span id="pctv">' + pct + '</span>%</b>' +
    '<input id="pct" type="range" min="' + MIN_PERCENT + '" max="' + MAX_PERCENT + '" value="' + pct + '"' +
    ' oninput="document.getElementById(\'pctv\').textContent=this.value;' +
    'document.querySelector(\'input[name=mode][value=\\\'' + CUSTOM + '\\\']\').checked=true">' +
    '<small>100% is original scale, 136% fills the width.</small></span></div>' +
    '<h2>Display panel</h2>' +
    option('panel', panel, PANEL_GRAY, 'Octagon', 'The real watch\'s LCD panel shape in dark gray, on black.') +
    option('panel', panel, PANEL_INVERTED, 'Inverted', 'A black octagon with dark gray around it.') +
    option('panel', panel, PANEL_OFF, 'Off', 'All black.') +
    '<h2>Panel shade</h2>' +
    option('shade', shade, SHADE_SOLID, 'Dark gray', 'Solid #555555, the darkest gray the screen has.') +
    option('shade', shade, SHADE_DARKER, 'Darker', 'Every other pixel gray, close to the real LCD.') +
    option('shade', shade, SHADE_DARKEST, 'Darkest', 'One pixel in four gray.') +
    '<h2>Seconds</h2>' +
    option('secs', secs, SECONDS_OFF, 'Off', 'Saves battery: the watch only wakes once a minute.') +
    option('secs', secs, SECONDS_ON, 'Seconds', 'Like the real watch.') +
    option('secs', secs, SECONDS_TEMPERATURE, 'Temperature',
      'Current temperature from the Pebble app\'s weather plugin, in your units. Needs plugins turned on ' +
      'in the Pebble app and the Location permission. Shows -- until a reading arrives.') +
    '<h2>Time zone</h2>' +
    option('tz', tz, TZ_DST, 'DST indicator', 'Like the real watch: DST while daylight saving time is on.') +
    option('tz', tz, TZ_NAME, 'Time zone', 'The zone\'s abbreviation, such as EST or CEST, in the same spot.') +
    option('tz', tz, TZ_OFF, 'Off', 'Nothing there.') +
    '<h2>Indicators</h2>' + INDICATORS.map(check).join('') +
    '<button id="save">Save</button><script>' +
    'function pick(n){return Number(document.querySelector("input[name="+n+"]:checked").value);}' +
    'document.getElementById("save").onclick=function(){' +
    'var ind=0;[].forEach.call(document.querySelectorAll(".ind"),function(c){' +
    'if(c.checked!==c.classList.contains("inv"))ind|=Number(c.value);});' +
    'location.href="pebblejs://close#"+encodeURIComponent(JSON.stringify({ScaleMode:pick("mode"),' +
    'ScalePercent:Number(document.getElementById("pct").value),Indicators:ind,' +
    'SecondsMode:pick("secs"),TzMode:pick("tz"),PanelMode:pick("panel"),PanelShade:pick("shade")}));};' +
    '</script></body></html>';
}

function send(msg, what) {
  Pebble.sendAppMessage(msg, function () {}, function () {
    console.log('GBD-200: could not send ' + what + ' to the watch.');
  });
}

// ---- Temperature from the weather plugin ----------------------------------

var weatherSubscription = null;

// The plugin's shortText is already in the user's units ("72°F", "-3°C");
// numericValue is always Celsius, so the number is read from the text.
function temperatureOf(envelope) {
  var place = envelope && envelope.instances && envelope.instances[0];
  var reading = place && place.properties && place.properties.temperature;
  var text = reading && reading.shortText && reading.shortText.text;
  if (!text) return null;
  var m = String(text).replace('−', '-').match(/-?\d+/);
  return m ? parseInt(m[0], 10) : null;
}

function updateWeatherSubscription(settings) {
  var wanted = settings.SecondsMode === SECONDS_TEMPERATURE;
  if (!wanted && weatherSubscription) {
    weatherSubscription.unsubscribe();
    weatherSubscription = null;
  }
  if (!wanted || weatherSubscription) return;
  if (typeof Pebble.subscribeToSource !== 'function') {
    console.log('GBD-200: this Pebble app has no plugin support, so no temperature.');
    return;
  }
  weatherSubscription = Pebble.subscribeToSource({
    category: 'weather',
    item: 'location',
    properties: ['temperature'],
    onData: function (envelope) {
      var t = temperatureOf(envelope);
      if (t === null) return;
      var msg = {};
      msg[keys.Temperature] = t;
      send(msg, 'the temperature');
    },
    // Errors (e.g. PERMISSION_DENIED while the request is pending) don't end
    // the subscription; the watch keeps its last reading until it goes stale.
    onError: function (err) {
      console.log('GBD-200: weather plugin: ' + (err && (err.code || err.message)));
    }
  });
}

Pebble.addEventListener('ready', function () {
  updateWeatherSubscription(loadSettings());
});

Pebble.addEventListener('showConfiguration', function () {
  Pebble.openURL('data:text/html;charset=utf-8,' + encodeURIComponent(pageHtml(loadSettings())));
});

Pebble.addEventListener('webviewclosed', function (e) {
  if (!e || !e.response) return;  // closed without saving
  var settings;
  try {
    settings = JSON.parse(decodeURIComponent(e.response));
  } catch (err) {
    console.log('GBD-200: settings page sent something unreadable.');
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  var msg = {};
  msg[keys.ScaleMode] = oneOf(settings.ScaleMode, [FILL, ORIGINAL, REAL, CUSTOM], FILL);
  if (typeof settings.ScalePercent === 'number') msg[keys.ScalePercent] = settings.ScalePercent;
  if (typeof settings.Indicators === 'number') msg[keys.Indicators] = settings.Indicators;
  msg[keys.SecondsMode] = oneOf(settings.SecondsMode, [SECONDS_OFF, SECONDS_ON, SECONDS_TEMPERATURE], SECONDS_OFF);
  msg[keys.TzMode] = oneOf(settings.TzMode, [TZ_DST, TZ_NAME, TZ_OFF], TZ_DST);
  msg[keys.PanelMode] = oneOf(settings.PanelMode, [PANEL_GRAY, PANEL_INVERTED, PANEL_OFF], PANEL_GRAY);
  msg[keys.PanelShade] = oneOf(settings.PanelShade, [SHADE_SOLID, SHADE_DARKER, SHADE_DARKEST], SHADE_DARKER);
  send(msg, 'settings');
  updateWeatherSubscription(settings);
});

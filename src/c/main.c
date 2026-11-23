// GBD-200: the G-SHOCK GBD-200's main time display, dot for dot.
//
// Everything is laid out in "dots" - the real watch's LCD pixels, measured
// from photos - and drawn at a chosen scale: 4/3 to fill the Time 2's width,
// one dot per pixel, real size (110%, matched by eye against the watch), or
// a custom percentage.

#include <pebble.h>
#include <limits.h>
#include "glyphs.auto.h"

#define PERSIST_SCALE_MODE 1
#define PERSIST_INDICATORS 2
#define PERSIST_SCALE_PERCENT 3
#define PERSIST_SHOW_SECONDS 4  // older on/off setting, read once to migrate
#define PERSIST_SECONDS_MODE 5
#define PERSIST_TEMPERATURE 6
#define PERSIST_TEMPERATURE_TIME 7
#define PERSIST_TZ_MODE 8
#define PERSIST_PANEL_MODE 9
#define PERSIST_PANEL_SHADE 10

enum { SCALE_FILL = 0, SCALE_ORIGINAL = 1, SCALE_REAL = 2, SCALE_CUSTOM = 3 };

// What the seconds digits show (matches src/pkjs/index.js).
enum { SECONDS_OFF = 0, SECONDS_ON = 1, SECONDS_TEMPERATURE = 2 };

// What sits where the watch shows DST (matches src/pkjs/index.js).
enum { TZ_DST = 0, TZ_NAME = 1, TZ_OFF = 2 };

// The LCD panel's octagon behind the display (matches src/pkjs/index.js).
enum { PANEL_GRAY = 0, PANEL_INVERTED = 1, PANEL_OFF = 2 };
enum { SHADE_SOLID = 0, SHADE_DARKER = 1, SHADE_DARKEST = 2 };

// The phone sends the temperature as the weather plugin reports it; a reading
// older than this is shown as "--".
#define TEMPERATURE_MAX_AGE (3 * 60 * 60)

#define REAL_SIZE_PERCENT 110  // matched by eye against the real watch
#define MIN_PERCENT 100
#define MAX_PERCENT 136  // 147 dots * 1.36 = the full 200px width

// Bottom-strip indicators, as a bitmask (matches src/pkjs/index.js).
enum {
  IND_SNZ = 1 << 0,
  IND_SIGNAL = 1 << 1,  // alarm signal, shown while a Pebble alarm is set
  IND_MUTE = 1 << 2,
  IND_VIB = 1 << 3,
  IND_LT = 1 << 4,
  // 1 << 5 was an always-on "!"; it now follows the battery (IND_HIDE_LOW_BATTERY).
  IND_PLANE = 1 << 6,  // airplane icon while the phone is disconnected
  // The rest are shown by default; their bit hides them.
  IND_HIDE_CASE_TEXT = 1 << 7,     // PEBBLE / WR30M
  IND_HIDE_LOW_BATTERY = 1 << 8,   // "!" when the battery runs low, like the watch
  IND_HIDE_BUBBLE = 1 << 9,        // notification bubble (the count isn't available)
  IND_HIDE_BUTTON_LABELS = 1 << 10,  // REV / UP / RUN / DOWN beside the buttons
};

#define LOW_BATTERY_PERCENT 20
#define IND_DEFAULT (IND_SIGNAL | IND_MUTE | IND_VIB)

// The 144-pixel-wide screens (Pebble 2 / 2 Duo) are just narrower than the
// face's 147 dots, so there it's always drawn 1:1, right-aligned, with the
// only things in the 3 spare dots - the P and an hour-tens digit - nudged
// right. Their pixels are close to the real watch's dot size anyway.
#if PBL_DISPLAY_WIDTH < 160
#define NARROW_SCREEN 1
#define NARROW_SHIFT 3
#else
#define NARROW_SCREEN 0
#define NARROW_SHIFT 0
#endif

// The face's bounds on the real LCD, in dots.
#define FACE_X 12
#define FACE_Y 8
#define FACE_W 147
#define FACE_H 121

static Window *s_window;
static Layer *s_canvas;
static int s_scale_mode = SCALE_FILL;
static int s_scale_percent = REAL_SIZE_PERCENT;  // used by SCALE_CUSTOM
static int s_indicators = IND_DEFAULT;
static bool s_bt_connected;
static bool s_battery_low;
static int s_seconds_mode = SECONDS_OFF;
static int s_tz_mode = TZ_DST;
static int s_panel_mode = PANEL_GRAY;
static int s_panel_shade = SHADE_DARKER;
static bool s_have_temperature;
static int s_temperature;
static time_t s_temperature_time;

// Dot-to-pixel mapping for the current mode: a span of n dots is
// round(n * num / den) pixels. A glyph's corner is placed by that rule; inside
// the glyph, the extra pixels go to the columns and rows planned for its
// family, so strokes stay even and every copy of a digit is identical.
static int s_off_x, s_off_y;
static int s_mapped_mode = -1, s_mapped_percent = -1;
static int16_t s_xmap[NUM_FAMILIES][MAX_GLYPH_W + 1];
static int16_t s_ymap[NUM_FAMILIES][MAX_GLYPH_H + 1];

// Pixels per dot for the current mode, as num / den.
static void scale_ratio(int *num, int *den) {
  if (NARROW_SCREEN) {
    *num = *den = 1;
    return;
  }
  switch (s_scale_mode) {
    case SCALE_ORIGINAL: *num = 1; *den = 1; break;
    case SCALE_REAL: *num = REAL_SIZE_PERCENT; *den = 100; break;
    case SCALE_CUSTOM: *num = s_scale_percent; *den = 100; break;
    default: *num = 4; *den = 3; break;
  }
}

static int scale(int dots) {
  int num, den;
  scale_ratio(&num, &den);
  // Round half away from zero, so a position left of or above the face
  // mirrors one to its right or below.
  if (dots < 0) return -((-dots * num * 2 + den) / (den * 2));
  return (dots * num * 2 + den) / (den * 2);
}

// Fills map[0..n] with the pixel offset of each of n dots along one axis:
// dots whose bit is set in `mask` (planned by tools/scale_plan.py) are two
// pixels wide. If the plan gives fewer pixels than the exact scale - to keep
// strokes even - the glyph is centered in its box.
static void build_axis_map(int16_t *map, int n, uint64_t mask) {
  map[0] = 0;
  for (int i = 0; i < n; i++) map[i + 1] = map[i] + ((mask >> i) & 1 ? 2 : 1);
  int slack = scale(n) - map[n];
  for (int i = 0; i <= n; i++) map[i] += slack / 2;
}

static int scale_index(void) {
  if (NARROW_SCREEN) return 0;
  switch (s_scale_mode) {
    case SCALE_ORIGINAL: return 0;
    case SCALE_REAL: return REAL_SIZE_PERCENT - SCALE_INDEX_MIN_PERCENT;
    case SCALE_CUSTOM: return s_scale_percent - SCALE_INDEX_MIN_PERCENT;
    default: return SCALE_INDEX_FILL;
  }
}

static void update_mapping(GRect bounds) {
  int w = scale(FACE_W), h = scale(FACE_H);
  s_off_x = NARROW_SCREEN ? bounds.size.w - w : (bounds.size.w - w) / 2;
  s_off_y = (bounds.size.h - h) / 2;
  if (s_mapped_mode == s_scale_mode && s_mapped_percent == s_scale_percent) return;
  int si = scale_index();
  for (int f = 0; f < NUM_FAMILIES; f++) {
    build_axis_map(s_xmap[f], FAMILIES[f].w, FAMILIES[f].xmask[si]);
    build_axis_map(s_ymap[f], FAMILIES[f].h, FAMILIES[f].ymask[si]);
  }
  s_mapped_mode = s_scale_mode;
  s_mapped_percent = s_scale_percent;
}

static int px_x(int x) { return s_off_x + scale(x - FACE_X); }
static int px_y(int y) { return s_off_y + scale(y - FACE_Y); }

static void fill_dots(GContext *ctx, int x, int y, int w, int h) {
  int x0 = px_x(x), y0 = px_y(y);
  graphics_fill_rect(ctx, GRect(x0, y0, scale(w), scale(h)), 0, GCornerNone);
}

static void draw_glyph(GContext *ctx, const Glyph *g, int x, int y) {
  if (!g) return;
  int gx = px_x(x), gy = px_y(y);
  const int16_t *xm = s_xmap[g->fam], *ym = s_ymap[g->fam];
  for (int r = 0; r < g->h; r++) {
    uint32_t bits = g->rows[r];
    int y0 = gy + ym[r], y1 = gy + ym[r + 1];
    int c = 0;
    while (c < g->w) {
      if (!(bits & (1u << (g->w - 1 - c)))) { c++; continue; }
      int start = c;
      while (c < g->w && (bits & (1u << (g->w - 1 - c)))) c++;
      int x0 = gx + xm[start], x1 = gx + xm[c];
      graphics_fill_rect(ctx, GRect(x0, y0, x1 - x0, y1 - y0), 0, GCornerNone);
    }
  }
}

// Draws glyphs left to right with `gap` dots between them, centered on cx.
static void draw_word(GContext *ctx, const Glyph *const *glyphs, int n, int cx, int y, int gap) {
  int w = gap * (n - 1);
  for (int i = 0; i < n; i++) w += glyphs[i]->w;
  int x = cx - w / 2;
  for (int i = 0; i < n; i++) {
    draw_glyph(ctx, glyphs[i], x, y);
    x += glyphs[i]->w + gap;
  }
}

// Draws a glyph one bit per screen pixel, ignoring the face's scale.
static void draw_glyph_px(GContext *ctx, const Glyph *g, int x, int y) {
  for (int r = 0; r < g->h; r++) {
    for (int c = 0; c < g->w; c++) {
      if (g->rows[r] & (1u << (g->w - 1 - c))) graphics_fill_rect(ctx, GRect(x + c, y + r, 1, 1), 0, GCornerNone);
    }
  }
}

// Where the Time 2's buttons are, as y centers on the screen.
#define BUTTON_TOP_Y 57
#define BUTTON_MIDDLE_Y 114
#define BUTTON_BOTTOM_Y 171
#define LABEL_EDGE 1     // pixels between a label and the screen edge
#define LABEL_CLEARANCE 9  // margin the face must leave for the labels

// The watch's button labels, moved to the Time 2's buttons: REV by Back,
// UP and DOWN by Up and Down, and RUN's orange triangle (without the word)
// by Select.
// They run along the screen edges and only show if the face leaves room.
static void draw_button_labels(GContext *ctx, GRect bounds) {
  int w = bounds.size.w;
  if (px_x(FACE_X) < LABEL_CLEARANCE || px_x(FACE_X + FACE_W) > w - LABEL_CLEARANCE) return;
  int right = w - LABEL_EDGE;
  draw_glyph_px(ctx, &LABEL_REV, LABEL_EDGE, BUTTON_TOP_Y - LABEL_REV.h / 2);
  draw_glyph_px(ctx, &LABEL_UP, right - LABEL_UP.w, BUTTON_TOP_Y - LABEL_UP.h / 2);
  draw_glyph_px(ctx, &LABEL_DOWN, right - LABEL_DOWN.w, BUTTON_BOTTOM_Y - LABEL_DOWN.h / 2);
  graphics_context_set_fill_color(ctx, PBL_IF_COLOR_ELSE(GColorOrange, GColorWhite));
  draw_glyph_px(ctx, &LABEL_RUN, right - LABEL_RUN.w, BUTTON_MIDDLE_Y - LABEL_RUN.h / 2);
  graphics_context_set_fill_color(ctx, GColorWhite);
}

// The temperature in the seconds digits, with a degree mark after them.
// Two cells fit -9..99; a third cell to the left covers 100+ and -10 or below.
// No reading, or a stale one, shows "--".
static void draw_temperature(GContext *ctx) {
  static const int CELL_X[] = {91, 113, 135};  // hundreds, tens, ones
  bool fresh = s_have_temperature && time(NULL) - s_temperature_time <= TEMPERATURE_MAX_AGE;
  if (!fresh) {
    draw_glyph(ctx, &SEC_MINUS, CELL_X[1], 89);
    draw_glyph(ctx, &SEC_MINUS, CELL_X[2], 89);
    return;
  }
  int v = s_temperature < 0 ? -s_temperature : s_temperature;
  if (v > 199) v = 199;
  int cell = 2;
  do {
    draw_glyph(ctx, &SEC_DIGITS[v % 10], CELL_X[cell--], 89);
    v /= 10;
  } while (v > 0 && cell >= 0);
  if (s_temperature < 0 && cell >= 0) draw_glyph(ctx, &SEC_MINUS, CELL_X[cell], 89);
  draw_glyph(ctx, &DEGREE, 152, 89);
}

// The zone's abbreviation (EST, CEST, ...) in the DST label's lettering.
static void draw_tz_name(GContext *ctx, const struct tm *t) {
  int x = 19;
  for (int i = 0; i < TZ_LEN && t->tm_zone[i]; i++) {
    char c = t->tm_zone[i];
    if (c >= 'a' && c <= 'z') c -= 'a' - 'A';
    const Glyph *g = tz_glyph(c);
    if (!g) continue;
    draw_glyph(ctx, g, x, 22);
    x += g->w + 1;
  }
}

// The case printing around the LCD - CASIO above, WR20BAR below on the real
// watch - as PEBBLE and WR30M, where they'd sit, if they fit on screen.
static void draw_case_text(GContext *ctx, GRect bounds) {
  static const Glyph *const LOGO[] = {&LOGO_P, &LOGO_E, &LOGO_B, &LOGO_B, &LOGO_L, &LOGO_E};
  static const Glyph *const WR[] = {&WR_W, &WR_R, &WR_3, &WR_0, &WR_M};
  if (px_y(-15) < 0 || px_y(145) > bounds.size.h) return;
  draw_word(ctx, LOGO, ARRAY_LENGTH(LOGO), 88, -15, 2);
  draw_word(ctx, WR, ARRAY_LENGTH(WR), 88, 139, 2);
}

// The palette's darkest gray is #555555, so darker shades mix it with black
// in a fine pattern: every pixel (solid), every other one (~#2A2A2A), or one
// in four (~#151515). Black-and-white screens mix in white instead, which is
// much brighter, so they use 1 pixel in 4, 8 or 16.
static bool shade_pixel(int x, int y) {
#if PBL_COLOR
  switch (s_panel_shade) {
    case SHADE_SOLID: return true;
    case SHADE_DARKER: return ((x + y) & 1) == 0;
    default: return (x & 1) == 0 && (y & 1) == 0;
  }
#else
  switch (s_panel_shade) {
    case SHADE_SOLID: return (x & 1) == 0 && (y & 1) == 0;
    case SHADE_DARKER: return (y & 1) == 0 && (x & 3) == (y & 2);         // 1 in 8, staggered
    default: return (y & 3) == 0 && (x & 7) == ((y & 4) ? 4 : 0);  // 1 in 16, staggered
  }
#endif
}

// Fills the background straight into the frame buffer: black, with the real
// watch's LCD panel - an octagon with rounded corners (PANEL_OUTLINE, in
// 1/16 dots) - in dark gray, or the reverse when inverted.
static void draw_background(GContext *ctx, GRect bounds) {
  int num, den;
  scale_ratio(&num, &den);
  // Outline in 1/16 screen pixels.
  enum { N = ARRAY_LENGTH(PANEL_OUTLINE) };
  int32_t ox[N], oy[N];
  for (int i = 0; i < N; i++) {
    ox[i] = s_off_x * 16 + (PANEL_OUTLINE[i][0] - FACE_X * 16) * num / den;
    oy[i] = s_off_y * 16 + (PANEL_OUTLINE[i][1] - FACE_Y * 16) * num / den;
  }
  GBitmap *fb = graphics_capture_frame_buffer(ctx);
  if (!fb) return;
#if PBL_COLOR
  uint8_t dark = GColorDarkGray.argb, black = GColorBlack.argb;
#endif
  for (int y = 0; y < bounds.size.h; y++) {
    GBitmapDataRowInfo row = gbitmap_get_data_row_info(fb, y);
    // The panel's span on this row: where its edges cross the pixel centers.
    int32_t yc = y * 16 + 8, left = INT32_MAX, right = INT32_MIN;
    if (s_panel_mode != PANEL_OFF) {
      for (int i = 0; i < N; i++) {
        int j = (i + 1) % N;
        if ((oy[i] <= yc) == (oy[j] <= yc)) continue;
        int32_t x = ox[i] + (yc - oy[i]) * (ox[j] - ox[i]) / (oy[j] - oy[i]);
        if (x < left) left = x;
        if (x > right) right = x;
      }
    }
    for (int x = row.min_x; x <= row.max_x; x++) {
      int32_t xc = x * 16 + 8;
      bool inside = xc >= left && xc < right;
      bool gray = (s_panel_mode == PANEL_GRAY && inside) || (s_panel_mode == PANEL_INVERTED && !inside);
      bool lit = gray && shade_pixel(x, y);
#if PBL_COLOR
      row.data[x] = lit ? dark : black;
#else
      // 1 bit per pixel, least significant bit first.
      if (lit) row.data[x / 8] |= 1 << (x % 8);
      else row.data[x / 8] &= ~(1 << (x % 8));
#endif
    }
  }
  graphics_release_frame_buffer(ctx, fb);
}

static void canvas_update(Layer *layer, GContext *ctx) {
  GRect bounds = layer_get_bounds(layer);
  update_mapping(bounds);
  draw_background(ctx, bounds);
  graphics_context_set_fill_color(ctx, GColorWhite);

  time_t now = time(NULL);
  struct tm *t = localtime(&now);

  // Top row: link and status icons, then the date.
  // Like the watch in airplane mode, losing the phone drops the link icons.
  // The bubble holds the watch's notification count. Pebble apps can't read
  // notifications, so it is drawn without a number.
  if (s_bt_connected) {
    draw_glyph(ctx, &ICON_BT, 25, 8);
    if (!(s_indicators & IND_HIDE_BUBBLE)) draw_glyph(ctx, &ICON_BUBBLE, 36, 8);
  } else if (s_indicators & IND_PLANE) {
    draw_glyph(ctx, &ICON_PLANE, 56, 7);
  }
  if (s_tz_mode == TZ_DST && t->tm_isdst > 0) draw_glyph(ctx, &ICON_DST, 19, 22);
  if (s_tz_mode == TZ_NAME) draw_tz_name(ctx, t);

  int mon = t->tm_mon + 1, mday = t->tm_mday;
  if (mon >= 10) draw_glyph(ctx, &DATE_DIGITS[mon / 10], 81, 10);
  draw_glyph(ctx, &DATE_DIGITS[mon % 10], 95, 10);
  draw_glyph(ctx, &SLASH, 108, 10);
  if (mday >= 10) draw_glyph(ctx, &DATE_DIGITS[mday / 10], 117, 10);
  draw_glyph(ctx, &DATE_DIGITS[mday % 10], 131, 10);

  fill_dots(ctx, 15, 31, 144, 1);

  // Time. 12-hour mode shows a P before afternoon hours, like the watch.
  int hour = t->tm_hour;
  if (!clock_is_24h_style()) {
    if (hour >= 12) draw_glyph(ctx, &ICON_P, 12 + NARROW_SHIFT, 50);
    hour %= 12;
    if (hour == 0) hour = 12;
  }
  if (hour >= 10) draw_glyph(ctx, &BIG_DIGITS[hour / 10], 12 + NARROW_SHIFT, 39);
  draw_glyph(ctx, &BIG_DIGITS[hour % 10], 47, 39);
  draw_glyph(ctx, &ICON_COLON_DOT, 82, 44);
  draw_glyph(ctx, &ICON_COLON_DOT, 82, 67);
  draw_glyph(ctx, &BIG_DIGITS[t->tm_min / 10], 97, 39);
  draw_glyph(ctx, &BIG_DIGITS[t->tm_min % 10], 132, 39);

  // Lower row: weekday under a short rule, seconds to the right. Letters
  // sit in fixed 14-dot cells; the narrow I is centered in its cell.
  fill_dots(ctx, 15, 89, 88, 1);

  static const char *const DAYS[] = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"};
  const char *day = DAYS[t->tm_wday];
  for (int i = 0; day[i]; i++) {
    const Glyph *g = letter_glyph(day[i]);
    draw_glyph(ctx, g, 31 + 14 * i + (g->w < 11 ? (11 - g->w) / 2 : 0), 95);
  }

  if (s_seconds_mode == SECONDS_ON) {
    draw_glyph(ctx, &SEC_DIGITS[t->tm_sec / 10], 113, 89);
    draw_glyph(ctx, &SEC_DIGITS[t->tm_sec % 10], 135, 89);
  } else if (s_seconds_mode == SECONDS_TEMPERATURE) {
    draw_temperature(ctx);
  }

  // Bottom indicator strip.
  if (s_indicators & IND_SNZ) draw_glyph(ctx, &ICON_SNZ, 44, 120);
  time_t next_alarm;
  (void)next_alarm;  // unused where the SDK stubs the alarm service out (diorite)
  if ((s_indicators & IND_SIGNAL) && alarm_service_peek_next(&next_alarm)) {
    draw_glyph(ctx, &ICON_SIGNAL, 65, 120);
  }
  if (s_indicators & IND_MUTE) draw_glyph(ctx, &ICON_MUTE, 88, 119);
  if (s_indicators & IND_VIB) draw_glyph(ctx, &ICON_VIB, 103, 118);
  if (s_indicators & IND_LT) draw_glyph(ctx, &ICON_LT, 122, 120);
  if (s_battery_low && !(s_indicators & IND_HIDE_LOW_BATTERY)) draw_glyph(ctx, &ICON_ALERT, 135, 116);

  if (!(s_indicators & IND_HIDE_CASE_TEXT)) draw_case_text(ctx, bounds);
  if (!(s_indicators & IND_HIDE_BUTTON_LABELS)) draw_button_labels(ctx, bounds);
}

static void tick_handler(struct tm *tick_time, TimeUnits units_changed) {
  layer_mark_dirty(s_canvas);
}

static void bt_handler(bool connected) {
  s_bt_connected = connected;
  layer_mark_dirty(s_canvas);
}

static void battery_handler(BatteryChargeState state) {
  bool low = !state.is_charging && !state.is_plugged && state.charge_percent <= LOW_BATTERY_PERCENT;
  if (low != s_battery_low) {
    s_battery_low = low;
    layer_mark_dirty(s_canvas);
  }
}

// Seconds off means waking once a minute instead of every second.
static void subscribe_ticks(void) {
  tick_timer_service_subscribe(s_seconds_mode == SECONDS_ON ? SECOND_UNIT : MINUTE_UNIT, tick_handler);
}

static void inbox_received(DictionaryIterator *iter, void *context) {
  Tuple *t = dict_find(iter, MESSAGE_KEY_ScaleMode);
  if (t) {
    int mode = t->value->int32;
    s_scale_mode = mode >= SCALE_FILL && mode <= SCALE_CUSTOM ? mode : SCALE_FILL;
    persist_write_int(PERSIST_SCALE_MODE, s_scale_mode);
  }
  t = dict_find(iter, MESSAGE_KEY_ScalePercent);
  if (t) {
    int pct = t->value->int32;
    s_scale_percent = pct < MIN_PERCENT ? MIN_PERCENT : pct > MAX_PERCENT ? MAX_PERCENT : pct;
    persist_write_int(PERSIST_SCALE_PERCENT, s_scale_percent);
  }
  t = dict_find(iter, MESSAGE_KEY_Indicators);
  if (t) {
    s_indicators = t->value->int32;
    persist_write_int(PERSIST_INDICATORS, s_indicators);
  }
  t = dict_find(iter, MESSAGE_KEY_SecondsMode);
  if (t) {
    int mode = t->value->int32;
    s_seconds_mode = mode >= SECONDS_OFF && mode <= SECONDS_TEMPERATURE ? mode : SECONDS_OFF;
    persist_write_int(PERSIST_SECONDS_MODE, s_seconds_mode);
    subscribe_ticks();
  }
  t = dict_find(iter, MESSAGE_KEY_PanelMode);
  if (t) {
    int mode = t->value->int32;
    s_panel_mode = mode >= PANEL_GRAY && mode <= PANEL_OFF ? mode : PANEL_GRAY;
    persist_write_int(PERSIST_PANEL_MODE, s_panel_mode);
  }
  t = dict_find(iter, MESSAGE_KEY_PanelShade);
  if (t) {
    int shade = t->value->int32;
    s_panel_shade = shade >= SHADE_SOLID && shade <= SHADE_DARKEST ? shade : SHADE_DARKER;
    persist_write_int(PERSIST_PANEL_SHADE, s_panel_shade);
  }
  t = dict_find(iter, MESSAGE_KEY_TzMode);
  if (t) {
    int mode = t->value->int32;
    s_tz_mode = mode >= TZ_DST && mode <= TZ_OFF ? mode : TZ_DST;
    persist_write_int(PERSIST_TZ_MODE, s_tz_mode);
  }
  t = dict_find(iter, MESSAGE_KEY_Temperature);
  if (t) {
    s_temperature = t->value->int32;
    s_temperature_time = time(NULL);
    s_have_temperature = true;
    persist_write_int(PERSIST_TEMPERATURE, s_temperature);
    persist_write_int(PERSIST_TEMPERATURE_TIME, (int32_t)s_temperature_time);
  }
  layer_mark_dirty(s_canvas);
}

static void window_load(Window *window) {
  Layer *root = window_get_root_layer(window);
  s_canvas = layer_create(layer_get_bounds(root));
  layer_set_update_proc(s_canvas, canvas_update);
  layer_add_child(root, s_canvas);
}

static void window_unload(Window *window) {
  layer_destroy(s_canvas);
}

static void init(void) {
  if (persist_exists(PERSIST_SCALE_MODE)) s_scale_mode = persist_read_int(PERSIST_SCALE_MODE);
  if (persist_exists(PERSIST_SCALE_PERCENT)) s_scale_percent = persist_read_int(PERSIST_SCALE_PERCENT);
  if (persist_exists(PERSIST_INDICATORS)) s_indicators = persist_read_int(PERSIST_INDICATORS);
  if (persist_exists(PERSIST_SECONDS_MODE)) {
    s_seconds_mode = persist_read_int(PERSIST_SECONDS_MODE);
  } else if (persist_exists(PERSIST_SHOW_SECONDS) && persist_read_bool(PERSIST_SHOW_SECONDS)) {
    s_seconds_mode = SECONDS_ON;
  }
  if (persist_exists(PERSIST_TZ_MODE)) s_tz_mode = persist_read_int(PERSIST_TZ_MODE);
  if (persist_exists(PERSIST_PANEL_MODE)) s_panel_mode = persist_read_int(PERSIST_PANEL_MODE);
  if (persist_exists(PERSIST_PANEL_SHADE)) s_panel_shade = persist_read_int(PERSIST_PANEL_SHADE);
  if (persist_exists(PERSIST_TEMPERATURE) && persist_exists(PERSIST_TEMPERATURE_TIME)) {
    s_temperature = persist_read_int(PERSIST_TEMPERATURE);
    s_temperature_time = persist_read_int(PERSIST_TEMPERATURE_TIME);
    s_have_temperature = true;
  }

  s_window = window_create();
  window_set_background_color(s_window, GColorBlack);
  window_set_window_handlers(s_window, (WindowHandlers) {
    .load = window_load,
    .unload = window_unload,
  });
  window_stack_push(s_window, true);

  s_bt_connected = connection_service_peek_pebble_app_connection();
  connection_service_subscribe((ConnectionHandlers) {.pebble_app_connection_handler = bt_handler});
  subscribe_ticks();
  battery_handler(battery_state_service_peek());
  battery_state_service_subscribe(battery_handler);

  app_message_register_inbox_received(inbox_received);
  app_message_open(64, 64);
}

static void deinit(void) {
  tick_timer_service_unsubscribe();
  battery_state_service_unsubscribe();
  connection_service_unsubscribe();
  window_destroy(s_window);
}

int main(void) {
  init();
  app_event_loop();
  deinit();
}

# ארכיטקטורת ה‑UI הגרפי — KungFu Chess

מסמך זה מסביר את שכבת ה‑UI הגרפית שנבנתה מעל ליבת המשחק הקיימת: איך היא בנויה,
אילו החלטות עומדות מאחוריה, ואיך מרחיבים אותה בהמשך (רשת, ריבוי שחקנים, פיצ'רים).

## סקירה

הליבה (`board/`, `rules/`, `realtime/`, `game/`, `view/`) לא שונתה במהותה — היא כבר
הפרידה לוגיקה מתצוגה. שכבת ה‑UI נוספה **לצידה**: חלון בזמן אמת, ציור כלים דרך `Img`,
אנימציות לפי מכונת‑מצבים, קלט עכבר, ו‑HUD. המסלול הפקודתי (`main.py`) ובודק ה‑VPL
נשארו שלמים.

כל גרפיקה עוברת דרך מחלקת `Img` (עוטפת OpenCV) — כפי שהמטלה דורשת.

## מפת השכבות

```
graphics/                # מתאמי cv2 — היחידים שמייבאים OpenCV
  img.py                 # Img מיובא מ‑CTD26 (פרימיטיב הציור). לא שונה
  window.py              # Window: חלון cv2 + קלט (imshow/waitKey/mouse-callback)
  assets.py              # read_image (טעינה Unicode-safe), AssetLoader, solid, white→alpha
  sprite.py              # SpriteAnimation: פריים לפי זמן (loop / one-shot)
  sprite_library.py      # SpriteLibrary: חיפוש אנימציה לפי token+state (+ תרגום token→תיקייה)

ui/                      # שכבת תצוגה/קלט — בלי cv2, בלי engine
  graphics_renderer.py   # GraphicsRenderer: מרכיב RenderModel על הלוח דרך Img
  hud.py                 # Hud: score, זמן, באנר game-over
  input_source.py        # InputTranslator: אירוע-מכשיר → פקודת-Controller
  # game loop יושב ב-play.py

gateway/
  gateway.py             # GameGateway (Protocol) + NetworkGateway (שלד עתידי)

view/
  render_model.py        # RenderModel / RenderPiece — DTO קפוא לתצוגה
  snapshot.py, renderer.py  # המודל/רנדרר הטקסטואלי הקיים (VPL) — לא שונה

play.py                  # נקודת כניסה גרפית + composition root + לולאת המשחק
assets/                  # board.png, board.csv, pieces/ (מ‑CTD26) + ATTRIBUTION.md
```

## התפרים המרכזיים (מה שהופך את זה ל"רציני")

1. **`GameGateway` — חוזה בלבד.** ה‑UI תלוי ב‑Protocol הזה, לא ב‑`GameEngine`
   הקונקרטי. אין מחלקה עוטפת כפולה: ה‑`GameEngine` הקיים **מקיים את החוזה ישירות**,
   אז הלוגיקה נשארת בעותק יחיד. זהו התפר שיאפשר רשת בעתיד (`NetworkGateway`) בלי
   לגעת ב‑UI.

2. **`RenderModel` — DTO קפוא.** מה שעובר לתצוגה הוא read‑model בלתי‑משתנה (כמו
   `GameSnapshot`, רק עשיר יותר: לכל כלי מצב + התקדמות‑מהלך). לא מדליפים `Board` חי.
   זה בדיוק מה ששרת סמכותי היה מסדרן ושולח ללקוח דק.

3. **`cv2` מבודד לחבילת `graphics/` בלבד** — `Img` (ציור), `Window` (חלון+קלט)
   וטעינת הנכסים. כל השאר (engine, ui, gateway) נקי מ‑cv2. ציור = רק דרך `Img`.

4. **הזמן מוזרק (dt).** הלולאה מודדת זמן‑קיר וממירה ל‑dt שמוזרק ל‑`engine.wait(dt)`;
   הליבה עיוורת‑לשעון. זה מה שיאפשר בעתיד שרת שמחזיק את השעון הסמכותי, ובזכות
   הדטרמיניזם — לסדר מהלכים מתנגשים לפי timestamp כך שכל הלקוחות מתכנסים.

## מכונת המצבים של הכלים (data-driven)

כל מצב מוגדר ב‑`assets/pieces/<CODE>/states/<STATE>/config.json` — fps, loop, מהירות,
והמצב הבא. המעברים (כפי שהנכסים מגדירים):

```
idle ──(מהלך)──▶ move ──(הגעה)──▶ long_rest ──▶ idle
idle ──(קפיצה)─▶ jump ──(נחיתה)─▶ short_rest ─▶ idle
```

- **move / jump** — ה‑arbiter מחזיק את התנועה; `render_model` מדווח `state="move"` עם
  `origin`/`progress`, וה‑renderer מחליק את הכלי בין התאים.
- **long_rest / short_rest** — cooldown אמיתי: אחרי מהלך/קפיצה הכלי נכנס למנוחה,
  **אסור לו לזוז** (`Reason.RESTING`) ואי אפשר לבחור בו, וה‑render מציג את אנימציית
  המנוחה. משכי המנוחה ב‑`config/settings.py`; אם מציבים 0 — אין cooldown (התנהגות
  המסלול הפקודתי/VPL נשמרת).

## זרימת פריים (הלולאה ב‑play.run)

```
dt = זמן-קיר שחלף
engine.wait(dt)                 # קידום השעון המדומה + יישוב הגעות/cooldown
model = engine.render_model()   # DTO סמכותי
canvas = renderer.render(model, base, selected)   # לוח+כלים+הדגשה, דרך Img
hud.draw(canvas, model)         # score/זמן/באנר
window.show(canvas)             # imshow
for event in window.poll_events():   # קליק שמאלי=בחירה/מהלך, ימני=קפיצה
    ...
```

## פורמט tokens והתרגום

הליבה משתמשת בפורמט `<צבע-קטן><סוג-גדול>` (`wP`, `bK`) — כל המנוע מסתמך על
`token[0]==צבע`. נכסי CTD26 משתמשים ב‑`<סוג><צבע>` גדול (`PW`, `KB`). התרגום 1:1 קורה
**רק בשתי נקודות‑מתאם**: `load_csv_board` (קלט) ו‑`SpriteLibrary.token_to_code` (חיפוש
sprite). הליבה לא רואה לעולם את הפורמט החיצוני.

## איך מריצים

```
pip install -r requirements.txt
python play.py
```

שליטה: **קליק שמאלי** על כלי לבחירה, קליק שמאלי על יעד למהלך; **קליק ימני** לקפיצה;
**ESC / q** ליציאה.

> הערה: `cv2.imread` לא קורא נתיבים עם תווים לא‑אנגליים ב‑Windows (הנתיב של הפרויקט
> מכיל עברית), לכן טעינת התמונות עוברת דרך `read_image` (‏`np.fromfile`+`imdecode`).

## איך מרחיבים בהמשך

- **רשת / שרת‑לקוח:** לממש את `NetworkGateway` (השלד ב‑`gateway/gateway.py`) — אותן
  חמש מתודות מעל רשת, מול `GameEngine` שרץ בשרת. ה‑UI לא משתנה, כי הוא תלוי רק ב‑Protocol.
- **ריבוי שחקנים בו‑זמנית:** מקור‑קלט = `InputTranslator` אחד עם `Controller` משלו.
  שחקן שני = זוג (מקור, controller) נוסף שמנותב לאותו gateway. ה‑engine כבר תומך
  ב‑`ALLOW_CONCURRENT_MOVES`. אכיפת בעלות‑לפי‑צבע היא התוספת היחידה שנשארת.
- **פיצ'רים בתצוגה** (ערכות‑נושא, סאונד, replay) — נוספים ב‑`ui/`/`graphics/` בלבד.
- **פיצ'רים בחוקים** (כלי חדש, תנאי‑ניצחון) — נוספים ב‑`rules/` דרך ה‑registry הקיים.

## בדיקות וכיסוי

הלוגיקה כולה מכוסה ב‑100% (ראה `.coveragerc`). המעטפת הגרפית (`Window`, לולאת
`play.run`) מסומנת `pragma: no cover`, ו‑`Img` המיובא מוחרג ככוד צד‑שלישי. הרכיבים
הטהורים (אנימציה, טעינת נכסים, RenderModel, cooldown, קלט, HUD, renderer) נבדקים
ביחידה, חלקם עם `Img` מזויף שמתעד קריאות ציור.

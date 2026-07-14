# מדריך קבצים — הערות בעברית על כל קובץ

עוברים על כל קובץ בפרויקט ומסבירים בשורה מה תפקידו. מסודר לפי שכבה, מהליבה כלפי
ה‑UI. להסבר זורם ראה [UI_OVERVIEW_HE.md](UI_OVERVIEW_HE.md); לארכיטקטורה ראה
[UI_ARCHITECTURE.md](UI_ARCHITECTURE.md).

## הגדרות

| קובץ | תפקיד |
|---|---|
| `config/settings.py` | כל הקבועים במקום אחד: גדלי לוח/תא, משכי מהלך/קפיצה/מנוחה, צבעים, נתיבי נכסים, גודל חלון. |

## הלוח (`board/`)

| קובץ | תפקיד |
|---|---|
| `board/board.py` | `Board` — הייצוג הפנימי היחיד של הלוח (מי בכל תא). קריאה/כתיבה/גבולות. |
| `board/loaders.py` | ממירים קלט ל‑`Board`: `load_text_board` (טקסט, ל‑VPL) ו‑`load_csv_board` (ה‑CSV של CTD26, עם תרגום `PW→wP`). |

## חוקי המשחק (`rules/`)

| קובץ | תפקיד |
|---|---|
| `rules/movement_strategy.py` | הממשק `MovementStrategy` + הקשר המהלך — כל סוג כלי מממש אותו. |
| `rules/piece_rules.py` | חוקי התנועה לכל כלי: מלך, מלכה, צריח, רץ, פרש, רגלי. |
| `rules/rule_registry.py` | `PieceRuleRegistry` — ממפה אות‑כלי לאסטרטגיית‑תנועה (נקודת ההרחבה לכלים חדשים). |
| `rules/rule_engine.py` | `RuleEngine` — בדיקת חוקיות מהלך (קריאה בלבד), מחזיר `MoveValidation`. |
| `rules/game_conditions.py` | אסטרטגיות תנאי‑ניצחון (`KingCaptureWinCondition`) וקידום רגלי (`LastRankPromotion`). |
| `rules/reasons.py` | `Reason` — קודי‑תוצאה יציבים למהלך (OK, RESTING, GAME_OVER...). |

## זמן אמת (`realtime/`)

| קובץ | תפקיד |
|---|---|
| `realtime/models.py` | `Move` / `Jump` (תנועות באוויר) ו‑`MotionView` (צילום מהלך עם אחוז‑התקדמות לתצוגה). |
| `realtime/real_time_arbiter.py` | `RealTimeArbiter` — לב הזמן‑אמת: שעון, הגעות, יירוט קפיצות, ו‑cooldown אחרי מהלך/קפיצה. |

## תיאום המשחק (`game/`)

| קובץ | תפקיד |
|---|---|
| `game/models.py` | `MoveResult` — תוצאת פקודה בגבול המנוע (התקבל/נדחה + סיבה). |
| `game/parser.py` | מפריד סקריפט‑פקודות לחלקי "Board" ו‑"Commands" (המסלול הטקסטואלי). |
| `game/board_mapper.py` | `BoardMapper` — ממיר פיקסל לתא (היחיד שיודע את גודל התא). |
| `game/controller.py` | `Controller` — מחזיק את מצב‑הבחירה ומתרגם קליק/קפיצה לפקודות מנוע. |
| `game/engine.py` | `GameEngine` — המתאם הראשי: מקבל פקודות, מפעיל חוקים/arbiter, חושף `render_model`. |

## מודלי תצוגה (`view/`)

| קובץ | תפקיד |
|---|---|
| `view/snapshot.py` | `GameSnapshot` — צילום‑מצב טקסטואלי (למסלול ה‑VPL). |
| `view/render_model.py` | `RenderModel`/`RenderPiece` — צילום‑מצב עשיר לתצוגה הגרפית (מצב + התקדמות לכל כלי). |
| `view/renderer.py` | `BoardRenderer` — הופך snapshot לטקסט. |

## גרפיקה — מתאמי OpenCV (`graphics/`)

| קובץ | תפקיד |
|---|---|
| `graphics/img.py` | `Img` — פרימיטיב הציור המצורף (מ‑CTD26). כל ציור עובר דרכו. לא שונה. |
| `graphics/window.py` | `Window` — חלון cv2 + קלט (imshow/waitKey/עכבר). המקום היחיד עם חלון+קלט. |
| `graphics/assets.py` | `read_image` (טעינה Unicode‑safe), `AssetLoader` (טעינת sprites), `solid` (מלבן‑כיסוי), `_white_to_alpha` (שקיפות). |
| `graphics/sprite.py` | `SpriteAnimation` — רצף פריימים; "איזה פריים בזמן t" (לולאה או חד‑פעמי). |
| `graphics/sprite_library.py` | `SpriteLibrary` — חיפוש אנימציה לפי token+מצב, כולל תרגום token→שם‑תיקייה. |

## תצוגה וקלט (`ui/`)

| קובץ | תפקיד |
|---|---|
| `ui/graphics_renderer.py` | `GraphicsRenderer` — מרכיב `RenderModel` על הלוח דרך `Img`: כלים, הדגשת‑בחירה, כיסוי‑אדום למנוחה. |
| `ui/hud.py` | `Hud` — ציור ניקוד/זמן/באנר game‑over ברצועה התחתונה. |
| `ui/input_source.py` | `InputTranslator` — ממפה אירוע‑עכבר של החלון לפקודת `Controller` (שמאל=מהלך, ימין=קפיצה). |

## התפר לעתיד (`gateway/`)

| קובץ | תפקיד |
|---|---|
| `gateway/gateway.py` | `GameGateway` (חוזה בלבד; ה‑engine מקיים אותו) + `NetworkGateway` (שלד לרשת עתידית). |

## נקודות כניסה

| קובץ | תפקיד |
|---|---|
| `main.py` | כניסה למסלול הפקודתי (טקסט / בודק VPL). |
| `play.py` | כניסה גרפית: בונה את המשחק ומריץ את לולאת הזמן‑אמת (`python play.py`). |

## נכסים (`assets/`)

| קובץ | תפקיד |
|---|---|
| `assets/board.png` | תמונת רקע הלוח. |
| `assets/board.csv` | מצב‑פתיחה סטנדרטי (פורמט CTD26 `KIND+COLOR`). |
| `assets/pieces/` | ה‑sprites לכל כלי×מצב (סט `pieces2` המצויר) + `config.json` לכל מצב. |
| `assets/ATTRIBUTION.md` | ייחוס מקור הנכסים (KamaTechOrg/CTD26). |

## בדיקות (`tests/`) והגדרות פרויקט

| קובץ | תפקיד |
|---|---|
| `tests/test_board.py`, `test_loaders.py`, `test_parser.py`, `test_registry.py`, `test_rules.py`, `test_rule_engine.py`, `test_game_conditions.py`, `test_snapshot.py` | בדיקות הליבה הקיימת. |
| `tests/test_real_time_arbiter.py`, `test_engine.py`, `test_controller.py`, `test_main.py` | בדיקות זמן‑אמת, מנוע, בקר, וכניסה. |
| `tests/test_assets.py`, `test_sprite.py`, `test_sprite_library.py` | בדיקות טעינת נכסים ואנימציה. |
| `tests/test_render_model.py`, `test_gateway.py`, `test_graphics_renderer.py`, `test_hud.py`, `test_input_source.py`, `test_play.py` | בדיקות שכבת ה‑UI (מודל‑תצוגה, gateway, רנדרר, HUD, קלט, הרכבה). |
| `conftest.py` | הגדרת נתיב הריצה של pytest. |
| `.coveragerc` | הגדרת כיסוי (מודד קוד‑מקור בלבד; מחריג את `Img` המיובא ואת המעטפת הגרפית). |
| `requirements.txt` | תלויות: `opencv-python`, `numpy`. |
| `docs/` | מסמכי הסבר (ארכיטקטורה, סקירה, מדריך הקבצים הזה). |

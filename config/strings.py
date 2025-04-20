# User-facing strings in Ukrainian
class Strings:
    # Command descriptions
    DAY_OFF_GROUP = "Команди для вихідних"
    DAY_OFF_THISWEEK = "Оберіть вихідні на ЦЕЙ тиждень."
    DAY_OFF_NEXTWEEK = "Оберіть вихідні на НАСТУПНИЙ тиждень."
    VACATION = "Вкажіть день/місяць початку та кінця відпустки."
    WORKLOAD_TODAY = "Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?"
    WORKLOAD_NEXTWEEK = "Скільки годин підтверджено на НАСТУПНИЙ тиждень?"
    CONNECTS = "Скільки CONNECTS Upwork Connects History показує ЦЬОГО тижня?"
    
    # Parameter descriptions
    START_DAY = "День початку відпустки (1-31)"
    START_MONTH = "Місяць початку відпустки"
    END_DAY = "День закінчення відпустки (1-31)"
    END_MONTH = "Місяць закінчення відпустки"
    CONNECTS_PARAM = "Кількість Upwork Connects, що залишилось на цьому тижні"

    # Messages
    SELECT_DAYS_THISWEEK = "Оберіть свої вихідні (цей тиждень):"
    SELECT_DAYS_NEXTWEEK = "Оберіть свої вихідні на наступний тиждень:"
    CONFIRM_BUTTON = "В кінці натисніть кнопку Підтверджую"
    SELECT_OPTION = "Оберіть варіант:"
    SELECT_HOURS = "Оберіть кількість годин:"  # Used for button views only

    # Errors
    GENERAL_ERROR = "Помилка: Не вдалося виконати команду."
    UNEXPECTED_ERROR = "Помилка: Сталася неочікувана помилка."
    INVALID_DAY = "День повинен бути між 1 та 31."
    VACATION_ERROR = "Ваш запит: Відпустка {start_day}/{start_month} - {end_day}/{end_month}\n{error}"
    CONNECTS_ERROR = "Ваш запит: Connects на цей тиждень = {connects}\n{error}"

    # Success/Processing
    PROCESSING = "⏳"
    ERROR = "❌"
    SURVEY_GREETING = "Готовий почати робочий день?"
    
    # Modal Titles
    WORKLOAD_TODAY_MODAL = "Години сьогодні"
    WORKLOAD_NEXTWEEK_MODAL = "Години наступного тижня"
    CONNECTS_MODAL = "Введіть кількість коннектів"
    DAY_OFF_MODAL = "Вихідні дні"
    
    # Modal Input Labels
    CONNECTS_INPUT = "Кількість коннектів"    
    
    # Modal Placeholders
    HOURS_PLACEHOLDER = "Введіть число (наприклад: 8)"
    CONNECTS_PLACEHOLDER = "Введіть число (наприклад: 80)"
    DAYS_PLACEHOLDER = "наприклад: пн, вт"
    
    # Modal Validation Errors
    NUMBER_REQUIRED = "Будь ласка, введіть числове значення."
    DAYS_REQUIRED = "Будь ласка, вкажіть дні вихідних."
    INPUT_SAVED = "Дякую! Ваші дані збережено."
    # UI prompts and errors
    CONNECTS_INPUT_PROMPT = f"{CONNECTS}\nВведіть кількість коннектів:"
    # Survey-specific errors
    STEP_ERROR = "Помилка при запуску кроку"
    NOT_YOUR_SURVEY_ERROR = "Це опитування не для вас."
    WRONG_CHANNEL_ERROR = "Це опитування не для цього каналу."
    # Survey-specific messages
    NOT_YOUR_SURVEY = "Це опитування не для вас."
    WRONG_CHANNEL = "Це опитування не для цього каналу."
    START_SURVEY_BUTTON = "Гайда"
    SURVEY_INPUT_BUTTON_LABEL = "Ввести"

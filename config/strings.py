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
    SELECT_DAYS_THISWEEK = "{user} Оберіть свої вихідні (цей тиждень):"
    SELECT_DAYS_NEXTWEEK = "{user} Оберіть свої вихідні на наступний тиждень:"
    CONFIRM_BUTTON = "В кінці натисніть кнопку Підтверджую"
    SELECT_OPTION = "Оберіть варіант:"
    WORKLOAD_TODAY_QUESTION = "{user} На скільки годин у тебе підтверджена зайнятість з СЬОГОДНІ до кінця тижня?"
    WORKLOAD_NEXTWEEK_QUESTION = "{user} Скажи, а чи є підтверджені завдання на наступний тиждень?"
    SELECT_HOURS = "Оберіть кількість годин:"

    # Errors
    GENERAL_ERROR = "Помилка: Не вдалося виконати команду."
    UNEXPECTED_ERROR = "Помилка: Сталася неочікувана помилка."
    INVALID_DAY = "День повинен бути між 1 та 31."
    VACATION_ERROR = "Ваш запит: Відпустка {start_day}/{start_month} - {end_day}/{end_month}\n{error}"
    CONNECTS_ERROR = "Ваш запит: Connects на цей тиждень = {connects}\n{error}"

    # Success/Processing
    PROCESSING = "⏳"
    ERROR = "❌"
# User-facing strings in Ukrainian
class Strings:
    # Command descriptions
    DAY_OFF_GROUP = "Команди для вихідних"
    CONNECTS_PLACEHOLDER = "Введіть число (наприклад: 80)"
    DAY_OFF_THISWEEK = "Оберіть вихідні на ЦЕЙ тиждень."
    DAY_OFF_NEXTWEEK = "Оберіть вихідні на НАСТУПНИЙ тиждень."
    WORKLOAD_TODAY = "Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?"
    WORKLOAD_NEXTWEEK = "Скільки годин підтверджено на НАСТУПНИЙ тиждень?"
    CONNECTS = "Скільки CONNECTS Upwork Connects History показує ЦЬОГО тижня?"
    VACATION = "Вкажіть день/місяць початку та кінця відпустки."

    # Parameter descriptions
    START_DAY = "День початку відпустки (1-31)"
    START_MONTH = "Місяць початку відпустки"
    END_DAY = "День закінчення відпустки (1-31)"
    END_MONTH = "Місяць закінчення відпустки"
    CONNECTS_PARAM = "Кількість Upwork Connects, що залишилось на цьому тижні"

    # Messages
    SELECT_HOURS = "Оберіть кількість годин:"
    SELECT_OPTION = "Оберіть варіант:"
    CONFIRM_BUTTON = "В кінці натисніть кнопку Підтверджую"

    # Errors
    GENERAL_ERROR = "Помилка: Не вдалося виконати команду."
    UNEXPECTED_ERROR = "Помилка: Сталася неочікувана помилка."
    INVALID_DAY = "День повинен бути між 1 та 31."
    NOT_YOUR_SURVEY = "Це опитування не для вас."
    WRONG_CHANNEL = "Це опитування не для цього каналу."
    DAYOFF_ERROR = "Ваша відповідь була: Вихідні дні = {days}\n{error}"
    WORKLOAD_ERROR = "Ваша відповідь булат: Навантаження = {hours}\n{error}"
    CONNECTS_ERROR = "Ваша відповідь була: Коннекти = {connects}\n{error}"
    SURVEY_EXPIRED_OR_NOT_FOUND = "Помилка: Опитування не знайдено або час його дії вичерпано."
    MODAL_SUBMIT_ERROR = "Помилка: Не вдалося обробити введення модального вікна."
    SURVEY_START_ERROR = "Помилка: Не вдалося розпочати опитування."
    STEP_ERROR = "Помилка: Проблема з кроком опитування."
    SURVEY_NOT_FOR_YOU = "Це опитування не призначене для вас."
    SURVEY_FINISH_ERROR = "Помилка: Не вдалося завершити опитування."

    # Success/Processing
    PROCESSING = "⏳"
    ERROR = "❌"
    SURVEY_GREETING = "Поділишся трохи планами?"

    # Modal Titles
    WORKLOAD_TODAY_MODAL = "Години сьогодні"
    WORKLOAD_NEXTWEEK_MODAL = "Години наступного тижня"
    CONNECTS_MODAL = "Введіть кількість коннектів"

    # Modal Validation Errors
    NUMBER_REQUIRED = "Будь ласка, введіть числове значення."

    # Survey-specific messages
    START_SURVEY_BUTTON = "Гайда"
    SURVEY_INPUT_BUTTON_LABEL = "Ввести"
    SURVEY_COMPLETE_MESSAGE = "Всі данні внесені. Дякую!"
    MENTION_MESSAGE = " <@&734125039955476501> зверніть увагу!"
    TIMEOUT_MESSAGE = '⏰ Час вийшов! Будь ласка, натисніть на кнопку **Гайда**, щоб ввести всі данні.'
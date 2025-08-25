# Response Templates from n8n Workflow

## Extracted Templates and Response Examples

### Registration Commands

#### Register Success
```
Канал успішно зареєстровано на {{ $json.property_name }}
```

**Example:**
```
Канал успішно зареєстровано на Сергій Шевчик
```

#### Already Registered
```
Канал вже зареєстрований на когось іншого.
```

#### Unregister Success
```
Готово. Тепер цей канал не зареєстрований ні на кого.
```

#### Unregister Not Found
```
Вибачте, але цей канал не зареєстрований ні на кого. Тому не можу зняти його з реєстрації
```

### Workload Commands

#### Workload Confirmation Template
```
Записав!
Заплановане навантаження у {Weekday}: {hours} год.
В щоденнику з понеділка до {Weekday}: {logged_hours} год.
Капасіті на цей тиждень: {capacity} год.
#{channel}    {time}
```

**Example (workload_today):**
```
Записав!
Заплановане навантаження у Понеділок: 8 год.
В щоденнику з понеділка до Понеділок: 8 год.
Капасіті на цей тиждень: 40 год.
#dev-serhii-shevchyk    15:30
```

**Example (workload_nextweek):**
```
Записав!
Заплановане навантаження у Вівторок: 6 год.
В щоденнику з понеділка до Вівторок: 14 год.
Капасіті на цей тиждень: 40 год.
#dev-serhii-shevchyk    15:30
```

### Day-off Commands

#### Day-off One Day Template
```
Записав!
Вихідний: {date}
#{channel}    {time}
```

**Example:**
```
Записав!
Вихідний: 2024-01-20
#dev-serhii-shevchyk    15:30
```

#### Day-off Multiple Days Template
```
Записав!
Вихідні: {date_list}
#{channel}    {time}
```

**Example:**
```
Записав!
Вихідні: 2024-01-20, 2024-01-21
#dev-serhii-shevchyk    15:30
```

#### Day-off None Template
```
Записав!
Вихідних немає
#{channel}    {time}
```

### Vacation Command

#### Vacation Template
```
Записав!
Відпустка: {start_date} - {end_date}
#{channel}    {time}
```

**Example:**
```
Записав!
Відпустка: 2024-02-01 - 2024-02-14
#dev-serhii-shevchyk    15:30
```

### Connects Command

#### Connects Template
```
Записав!
Коннекти на цьому тижні: {connects}
#{channel}    {time}
```

**Example:**
```
Записав!
Коннекти на цьому тижні: 5
#dev-serhii-shevchyk    15:30
```

### Survey Command

#### Survey Continue Template
```json
{
  "output": "Дякую! Продовжуємо опитування.",
  "survey": "continue"
}
```

#### Survey End Template
```json
{
  "output": "Дякую! Опитування завершено.",
  "survey": "end",
  "url": "https://notion.so/user-todo-page"
}
```

#### Survey Cancel Template
```json
{
  "output": "Опитування скасовано.",
  "survey": "cancel"
}
```

### Mention/Default Commands

#### Bot Mention Response
```
Я ще не вмію вільно розмовляти. Використовуй слеш команди <@{userId}>. Почни із /
```

**Example:**
```
Я ще не вмію вільно розмовляти. Використовуй слеш команди <@829736729991970838>. Почни із /
```

#### Error Response
```
Спробуй трохи піздніше. Я тут пораюсь по хаті.
```

#### General Error Response
```json
{
  "output": "Some error"
}
```

## Template Processing Rules

### From Basic LLM Chain + toJSON
- **Input**: AI Agent output with stringified JSON in "output" field
- **Processing**: Parse JSON from ```json fences or plain ``` fences
- **Output**: Valid JSON response
- **Critical**: Never remove `\n` or change to `\\n` - preserve exact newlines

### Response Schema Rules
1. **Non-survey commands**: `{ "output": "string" }`
2. **Survey commands**: `{ "output": "string", "survey": "continue|end|cancel" }`
3. **Survey end**: `{ "output": "string", "survey": "end", "url": "<to_do_URL>" }`

### Dynamic Value Placeholders
- `{user.name}` - User's name from Notion Team Directory
- `{userId}` - Discord user ID
- `{channelId}` - Discord channel ID
- `{channel}` - Channel name (without #)
- `{time}` - Current time formatted as HH:MM
- `{date}` - Date in YYYY-MM-DD format
- `{hours}` - Hours value
- `{capacity}` - Weekly capacity
- `{logged_hours}` - Accumulated logged hours
- `{Weekday}` - Day name in Ukrainian (Понеділок, Вівторок, etc.)
- `{connects}` - Number of connects
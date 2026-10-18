# OpenClaw на бесплатных моделях: полная инструкция «с нуля»

Инструкция собрана по реальной работающей системе (октябрь 2026): OpenClaw 2026.10.4, OmniRoute 3.8.51, Node 24, Ubuntu 24.04. Ключи, пароли, токены и адреса заменены на заглушки вида `<SERVER_IP>`, `<TAILNET>`, `<YOUR_OPENROUTER_KEY>`. Подставляйте свои.

Два варианта установки:

- **Вариант A:** OpenClaw на своём компьютере (macOS, Linux или Windows через WSL2).
- **Вариант B:** OpenClaw на сервере DigitalOcean. Так сделано у нас.

Разделы 4–10 одинаковы для обоих вариантов. Там, где есть разница, это помечено.

Все готовые файлы (скрипты, фрагменты конфигурации, systemd-юниты) лежат в папке [files/](files/).

---

## 1. Что получится

```text
 iPhone (приложение OpenClaw)                Боты-помощники (другие ИИ-агенты)
        │  wss://<TAILNET-HOST>                     │  ssh + oc-delegate / oc-mail
        ▼                                           ▼
 ┌──────────── Tailscale (частная сеть) ──┐   ┌──────── SSH (порт 22) ────────┐
 └───────────────────┬────────────────────┘   └───────────────┬───────────────┘
                     ▼                                        ▼
 ┌───────────────────────────── Сервер / компьютер ─────────────────────────────┐
 │  OpenClaw Gateway (127.0.0.1:18789, systemd user service)                    │
 │    ├─ агент main        ── координатор, сам раздаёт задачи ──┐               │
 │    ├─ агент guest       ── второй пользователь (своя память)─┤               │
 │    ├─ агент researcher  ── поиск и чтение в интернете   ◄────┤ subagents     │
 │    └─ агент worker      ── код и команды на сервере     ◄────┘ (макс. 2)     │
 │                                                                              │
 │  OmniRoute (127.0.0.1:20128) ── модель "auto": Gemini / Groq / NVIDIA        │
 │  Прямые провайдеры (запасные): OpenRouter :free, NVIDIA, Google, Groq, Z.ai  │
 │                                                                              │
 │  ~/bin/oc-gate (вход второго пользователя), ~/bin/ocmail.py (почта ботов)    │
 └──────────────────────────────────────────────────────────────────────────────┘
```

Как это работает:

- **Телефон** подключается к шлюзу (Gateway) через Tailscale Serve. Шлюз слушает только `127.0.0.1`, в интернет он не открыт.
- **Агенты.** `main` — главный, он сам передаёт работу `researcher` и `worker` (режим `delegationMode: "prefer"`). `guest` — отдельный агент второго пользователя со своей памятью, ему доступны те же помощники.
- **Модели** только бесплатные. Первой идёт `omniroute/auto`: OmniRoute сам выбирает живого бесплатного провайдера. Если он не ответил, OpenClaw идёт по списку запасных моделей.
- **Делегирование от ботов.** Другие ИИ-боты (например, на отдельной Linux-машине) отдают задачи командой `oc-delegate` по SSH и забирают только итоговый ответ. Боты разных людей обмениваются сообщениями через `oc-mail`. Второй пользователь входит по SSH-ключу, который пускает только в `oc-gate`.

---

## 2. Аккаунты и бесплатные ключи

Лимиты указаны по официальным страницам на октябрь 2026. Они меняются: перепроверяйте по ссылкам.

| Сервис | Где взять | Что даёт бесплатно | Важно |
|---|---|---|---|
| **OpenRouter** | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys), пополнение: [settings/credits](https://openrouter.ai/settings/credits) | Модели с суффиксом `:free` и роутер `openrouter/free`. 20 запросов в минуту; 50 в день, если куплено меньше $10 кредитов за всё время, и **1000 в день**, если куплено от $10 ([документация](https://openrouter.ai/docs/api/reference/limits)). | Мы один раз положили $10–11 **только** чтобы поднять дневной лимит. Кредиты тратятся лишь на платные модели. Поэтому никогда не используйте `openrouter/auto`: это платный роутер. |
| **Groq** | [console.groq.com/keys](https://console.groq.com/keys) | Для `openai/gpt-oss-120b`: 30 запросов в минуту, 1000 в день, 8 000 токенов в минуту, 200 000 в день ([rate limits](https://console.groq.com/docs/rate-limits)). | 8 000 токенов в минуту — это мало для большого системного промпта агента. Отсюда ошибка 413, см. раздел 9. |
| **Google Gemini (AI Studio)** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `gemini-3.8-flash`, `gemma-4-31b-it` на бесплатном уровне. Конкретные лимиты Google показывает в AI Studio, публичной таблицы нет ([rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)). | Карта не нужна. Условия бесплатного уровня смотрите в Terms Gemini API. |
| **NVIDIA NIM** | [build.nvidia.com](https://build.nvidia.com) → API key (`nvapi-…`) | `z-ai/glm-5.3` и другие модели | Это **пробные кредиты**, а не вечный бесплатный доступ. Когда кончатся, модель отвалится, и сработают запасные. |
| **Z.ai** | [z.ai](https://z.ai) → API keys; цены: [docs.z.ai/guides/overview/pricing](https://docs.z.ai/guides/overview/pricing) | `glm-4.7-flash` и `glm-4.5-flash` бесплатны (Free по всем статьям). | Остальные модели GLM платные. |
| **Tailscale** | [login.tailscale.com/start](https://login.tailscale.com/start) | Бесплатный личный тариф | Нужен для доступа с телефона. |
| **DigitalOcean** (только вариант B) | [cloud.digitalocean.com](https://cloud.digitalocean.com) | — | Droplet: $6/мес (1 ГБ) или $12/мес (2 ГБ, рекомендуем). |

Что мы проверили и **не** подключаем:

- **Kimi** — платный.
- **Cerebras** — требует карту.
- **GitHub Models** — закрыт с 30.07.2026.
- **SambaNova** — кредиты кончились, теперь требует карту.
- **Mistral** — на бесплатном тарифе постоянно отвечает 429.
- **Plugsky** — слабые модели.
- В OmniRoute: всё с пометкой `tos: avoid` (например, Kiro, OpenCode Free) и любые подписки через OAuth (Cursor, Grok, Claude), потому что за это могут забанить аккаунт.

> **Конфиденциальность.** У многих бесплатных моделей (Inkling, Nemotron и др. на OpenRouter) провайдер может обучаться на ваших запросах. Не отправляйте через них ничего приватного.

Ключи храните в менеджере паролей. Ниже они везде вводятся через stdin или `read -s`, чтобы не оставаться в истории shell.

---

<a id="variant-a"></a>
## 3A. Вариант A: установка на свой компьютер

Подходит, если компьютер почти всегда включён. Боты на других машинах смогут достучаться до него только по SSH (например, через Tailscale). Если компьютер часто спит, берите вариант B.

### 3A.1 Требования

- Node **24.16+** или 26.1+ ([docs.openclaw.ai/install](https://docs.openclaw.ai/install)). Установщик сам поставит Node, если его нет.
- macOS, Linux или Windows с **WSL2**. В WSL2 должен быть включён systemd: в `/etc/wsl.conf` добавьте
  ```ini
  [boot]
  systemd=true
  ```
  и перезапустите WSL командой `wsl --shutdown` в PowerShell.
- От 2 ГБ свободной памяти (OpenClaw и OmniRoute вместе).

### 3A.2 Установка OpenClaw

Официальный установщик для macOS, Linux и WSL2:

```bash
curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard
```

Если Node уже стоит, можно поставить через npm. На npm 11.16+ нужен флаг `--allow-scripts`; на npm 11.15 и старше команда та же, но без этого флага. Чтобы получить ровно нашу версию, вместо `@latest` укажите `@2026.10.4`:

```bash
npm install -g openclaw@latest --allow-scripts=openclaw
openclaw --version        # у нас: OpenClaw 2026.10.4
```

### 3A.3 Первичная настройка (onboarding)

```bash
openclaw onboard --install-daemon
```

В мастере выберите:

- **Mode:** `local`
- **Auth:** OpenRouter API key (`openrouter-api-key`), вставьте `<YOUR_OPENROUTER_KEY>`
- **Gateway bind:** `loopback`, **auth:** `token`
- **Tailscale:** `serve`, если нужен телефон (сначала сделайте раздел 7.1), иначе `off`
- **Channels:** пропустить (мы используем только приложение)

`--install-daemon` ставит службу. На macOS это LaunchAgent, на Linux и WSL2 — systemd user service `openclaw-gateway`.

Проверка:

```bash
openclaw doctor
openclaw gateway status
```

### 3A.4 OmniRoute на своём компьютере

На своём компьютере OmniRoute ставится так же, как на сервере (раздел 6). Отличаются только автозапуск и путь `DATA_DIR`.

- **Linux и WSL2:** используйте юнит [files/omniroute.service](files/omniroute.service), как в разделе 6.4. Встроенная команда `omniroute autostart enable` тоже создаёт systemd user service, но без наших ограничений памяти.
- **macOS:** systemd нет. Запускайте `omniroute serve --no-open --daemon --port 20128` или настройте свой LaunchAgent. Лимиты памяти вида `MemoryMax` на macOS недоступны.

В `~/.omniroute/.env` поставьте `DATA_DIR=$HOME/.omniroute` с вашим реальным путём, например `/Users/<you>/.omniroute`.

Дальше идите к разделу 4. Пути вида `/home/openclaw/...` в примерах замените на свой `$HOME`.

---

<a id="variant-b"></a>
## 3B. Вариант B: сервер DigitalOcean

### 3B.1 Создание droplet

Документация: [docs.digitalocean.com/products/droplets/how-to/create](https://docs.digitalocean.com/products/droplets/how-to/create/).

1. **Create → Droplets.**
2. **Region:** любой ближайший.
3. **Image:** Ubuntu 24.04 LTS x64.
4. **Size:** Basic → Regular. Минимум $6/мес (1 ГБ RAM, 1 vCPU). **Рекомендуем $12/мес (2 ГБ).** На 1 ГБ всё работает, но свободной памяти остаётся 50–90 МБ, простой ответ идёт до 1,5 минут, а шлюз стартует почти 2 минуты.
5. **Authentication:** лучше **SSH key** (добавьте свой `~/.ssh/id_ed25519.pub`). Если выбираете пароль: DigitalOcean не принимает пароль, который кончается цифрой, а поле ограничено 21 символом.
6. **Create Droplet**, запишите `<SERVER_IP>`.

Если начали с $6, перейти на 2 ГБ можно потом: **Power off → Resize → CPU and RAM only**. Диск и все настройки сохраняются ([документация по resize](https://docs.digitalocean.com/products/droplets/how-to/resize/)).

### 3B.2 Пользователь, swap, базовые пакеты

Под root:

```bash
ssh root@<SERVER_IP>

apt-get update && apt-get -y upgrade
apt-get install -y curl jq python3 git ca-certificates

# отдельный пользователь, под которым живёт OpenClaw
adduser openclaw                      # задайте пароль (нужен для sudo)
usermod -aG sudo openclaw
mkdir -p /home/openclaw/.ssh && cp ~/.ssh/authorized_keys /home/openclaw/.ssh/
chown -R openclaw:openclaw /home/openclaw/.ssh && chmod 700 /home/openclaw/.ssh && chmod 600 /home/openclaw/.ssh/authorized_keys

# службы пользователя работают без активного входа
loginctl enable-linger openclaw

# swap 2 ГБ (обязательно на 1–2 ГБ RAM)
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
swapon --show && free -m
```

### 3B.3 Node 24 (NodeSource)

У нас Node взят из репозитория NodeSource `node_24.x` (v24.22.0):

```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
apt-get install -y nodejs
node -v          # v24.x
```

Можно и без этого шага: официальный установщик OpenClaw сам ставит Node 24 LTS на Linux.

### 3B.4 OpenClaw

У нас OpenClaw стоит глобально в `/usr/lib/node_modules/openclaw`, бинарник `/usr/bin/openclaw`:

```bash
npm install -g openclaw@2026.10.4 --allow-scripts=openclaw   # или @latest; на npm ≤ 11.15 без --allow-scripts
openclaw --version
```

Дальше всё делаем **под пользователем `openclaw`**:

```bash
ssh openclaw@<SERVER_IP>
export XDG_RUNTIME_DIR=/run/user/$(id -u)    # нужно для systemctl --user в SSH-сессии
echo 'export XDG_RUNTIME_DIR=/run/user/$(id -u)' >> ~/.bashrc
echo 'export PATH=$HOME/.local/bin:$HOME/bin:$PATH' >> ~/.bashrc
```

### 3B.5 Onboarding и служба systemd

Сначала поставьте Tailscale (раздел 7.1), потом запускайте мастер:

```bash
openclaw onboard --install-daemon
```

Выбор в мастере тот же, что в 3A.3: `local`, OpenRouter API key, bind `loopback`, auth `token`, Tailscale `serve`, каналы пропустить.

<details markdown="1"><summary>Неинтерактивный вариант (флаги из <code>openclaw onboard --help</code>; мы в таком сочетании их не запускали)</summary>

```bash
read -rs OPENROUTER_KEY            # вставьте <YOUR_OPENROUTER_KEY>, Enter
openclaw onboard --non-interactive --accept-risk --mode local \
  --auth-choice openrouter-api-key --openrouter-api-key "$OPENROUTER_KEY" \
  --gateway-bind loopback --gateway-auth token --tailscale serve \
  --skip-channels --install-daemon
unset OPENROUTER_KEY
```

Ключ в аргументах командной строки виден в `ps` на время работы команды. На общем сервере лучше интерактивный мастер.
</details>

Мастер создаст `~/.config/systemd/user/openclaw-gateway.service`. Наш файл целиком лежит в [files/openclaw-gateway.service](files/openclaw-gateway.service). Ключевые строки:

```ini
ExecStart=/usr/bin/node --max-old-space-size=720 /usr/lib/node_modules/openclaw/dist/index.js gateway --port 18789
Restart=always
RestartSec=5
OOMPolicy=continue
KillMode=mixed
```

Если у вас в `ExecStart` нет `--max-old-space-size=720`, допишите его на 1 ГБ сервере: так Node не раздует кучу больше, чем есть памяти. Затем:

```bash
systemctl --user daemon-reload && systemctl --user restart openclaw-gateway
```

Команда `openclaw gateway install --force` перезапишет файл, тогда правку придётся повторить.

Проверка:

```bash
systemctl --user status openclaw-gateway
openclaw gateway status
openclaw doctor
```

На 1 ГБ шлюз поднимается до 2 минут. Пока он стартует, `gateway status` может показывать ошибку, это нормально.

---

## 4. Модели и запасные (fallbacks)

### 4.1 Ключи провайдеров

OpenRouter уже добавлен на onboarding (профиль `openrouter:default`). Остальные ключи передаются через stdin, чтобы не попасть в историю:

```bash
read -rs K; printf %s "$K" | openclaw models auth paste-api-key --provider groq;   unset K   # <YOUR_GROQ_KEY>
read -rs K; printf %s "$K" | openclaw models auth paste-api-key --provider nvidia; unset K   # <YOUR_NVIDIA_KEY>
read -rs K; printf %s "$K" | openclaw models auth paste-api-key --provider google; unset K   # <YOUR_GEMINI_KEY>
read -rs K; printf %s "$K" | openclaw models auth paste-api-key --provider zai;    unset K   # <YOUR_ZAI_KEY>
openclaw models auth list
```

Должны появиться `google:manual`, `groq:manual`, `nvidia:manual`, `zai:manual` и `openrouter:default`. Хранилище ключей общее для всех агентов (`~/.openclaw/state/openclaw.sqlite`), поэтому `researcher` и `worker` видят те же ключи.

### 4.2 Почему JSON, а не `openclaw config set`

`openclaw models set` и `openclaw models fallbacks add/clear/list` работают, но только для агента по умолчанию. У нас `openclaw config set` ломался на массивах fallbacks, поэтому модели всех агентов задаём одним JSON-фрагментом и сливаем его в `~/.openclaw/openclaw.json` через `jq`.

Фрагмент для моделей и агентов: [files/openclaw-models-agents.json](files/openclaw-models-agents.json). Главная часть:

```json
{
  "agents": {
    "defaults": {
      "models": {
        "omniroute/auto": {},
        "openrouter/thinkingmachines/inkling:free": {},
        "openrouter/thinkingmachines/inkling-small:free": {},
        "nvidia/z-ai/glm-5.3": {},
        "openrouter/nvidia/nemotron-3.5-super-vl:free": {},
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free": {},
        "groq/openai/gpt-oss-120b": {},
        "google/gemini-3.8-flash": {},
        "google/gemma-4-31b-it": {},
        "zai/glm-4.7-flash": {},
        "openrouter/nvidia/nemotron-3.5-lightning:free": {},
        "openrouter/free": {}
      },
      "model": {
        "primary": "omniroute/auto",
        "fallbacks": [
          "openrouter/thinkingmachines/inkling:free",
          "nvidia/z-ai/glm-5.3",
          "openrouter/nvidia/nemotron-3.5-super-vl:free",
          "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
          "groq/openai/gpt-oss-120b",
          "google/gemini-3.8-flash",
          "google/gemma-4-31b-it",
          "zai/glm-4.7-flash",
          "openrouter/nvidia/nemotron-3.5-lightning:free",
          "openrouter/free"
        ]
      }
    }
  },
  "models": {
    "providers": {
      "omniroute": {
        "baseUrl": "http://127.0.0.1:20128/v1",
        "api": "openai-completions",
        "apiKey": "${OMNIROUTE_API_KEY}",
        "models": [ { "id": "auto", "name": "OmniRoute auto (free providers)" } ]
      }
    }
  }
}
```

Пояснения:

- `agents.defaults.models` — это список разрешённых моделей. Модель, которой в нём нет, агент не возьмёт.
- `${OMNIROUTE_API_KEY}` подставляется из `~/.openclaw/.env` (шаблон: [files/openclaw.env.example](files/openclaw.env.example)). Сам ключ в JSON не пишется.
- Порядок запасных: сильные модели идут первыми, `openrouter/free` стоит последним как «хоть что-нибудь».

### 4.3 Как применить фрагмент

```bash
cd ~/.openclaw
cp openclaw.json openclaw.json.bak-$(date +%Y%m%d-%H%M%S)          # резервная копия
jq -s '.[0] * .[1] * .[2]' openclaw.json \
   ~/openclaw-models-agents.json ~/openclaw-gateway.json > /tmp/oc.json \
 && install -m 600 /tmp/oc.json openclaw.json && rm /tmp/oc.json
openclaw config validate          # должно быть: Config valid
openclaw gateway restart
openclaw models status
```

`jq '*'` сливает объекты рекурсивно, а массивы заменяет целиком, поэтому старые fallbacks не дублируются. Фрагменты мы проверили `openclaw config validate` на копии рабочего конфига.

Есть и штатный способ: `openclaw config patch --file <фрагмент> --dry-run`, потом без `--dry-run`. По справке объекты он тоже сливает, а массивы заменяет, но на fallbacks мы его не проверяли.

Если OmniRoute ещё не поставлен (раздел 6), сначала примените [files/openclaw-no-omniroute.json](files/openclaw-no-omniroute.json). В нём главная модель Inkling, а у исследователя — Inkling Small.

---

## 5. Агенты и ограничения подагентов

### 5.1 Создание агентов

Агент `main` создаётся на onboarding. Остальных добавьте так:

```bash
openclaw agents add researcher --workspace ~/.openclaw/workspace-researcher --non-interactive
openclaw agents add worker     --workspace ~/.openclaw/workspace-worker     --non-interactive
openclaw agents add guest       --workspace ~/.openclaw/workspace-guest       --non-interactive   # только если будет второй пользователь
openclaw agents list
```

Затем примените фрагмент из раздела 4.3, если ещё не сделали этого: он же задаёт модели и права агентов. Ниже эта часть фрагмента:

```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "maxConcurrent": 2,
        "maxSpawnDepth": 1,
        "maxChildrenPerAgent": 2,
        "runTimeoutSeconds": 600
      }
    },
    "entries": {
      "main":   { "subagents": { "allowAgents": ["researcher", "worker"], "delegationMode": "prefer" } },
      "guest":   { "subagents": { "allowAgents": ["researcher", "worker"], "delegationMode": "prefer" } },
      "researcher": {
        "model": { "primary": "omniroute/auto",
                   "fallbacks": ["openrouter/thinkingmachines/inkling-small:free", "google/gemini-3.8-flash",
                                 "groq/openai/gpt-oss-120b", "openrouter/free"] },
        "subagents": { "allowAgents": [] }
      },
      "worker": {
        "model": { "primary": "nvidia/z-ai/glm-5.3", "fallbacks": ["zai/glm-4.7-flash", "openrouter/free"] },
        "subagents": { "allowAgents": [] }
      }
    }
  }
}
```

| Агент | Роль | Модели |
|---|---|---|
| `main` | Координатор. Сам передаёт работу помощникам (`delegationMode: "prefer"`) | общие: `omniroute/auto` → Inkling → GLM-5.3 → … |
| `guest` | Агент второго пользователя, своя память и рабочая папка | общие, как у `main` |
| `researcher` | Поиск и чтение в интернете | `omniroute/auto` → Inkling Small → Gemini Flash → Groq → `openrouter/free` |
| `worker` | Код и команды на сервере | GLM-5.3 (NVIDIA) → GLM-4.7-Flash (Z.ai) → `openrouter/free` |

Ограничения: одновременно не больше 2 подагентов, без вложенности (помощники не порождают своих), таймаут задачи 10 минут. Больше на маленьком сервере не потянуть ни по памяти, ни по лимитам бесплатных моделей. Документация: [Sub-agents](https://docs.openclaw.ai/tools/subagents), [Multi-agent](https://docs.openclaw.ai/concepts/multi-agent).

Проверка делегирования:

```bash
openclaw agent --agent main --timeout 600 \
  --message "Найди через исследователя дату выхода Node 24 LTS и дай ссылку на источник. Коротко."
```

---

## 6. OmniRoute: один «умный» вход на бесплатных провайдеров

[OmniRoute](https://github.com/diegosouzapw/OmniRoute) (MIT) — локальный шлюз с OpenAI-совместимым API. Модель `auto` у него сама выбирает здорового провайдера и переключается при ошибках.

Правила, которых мы держимся:

- только бесплатные провайдеры по своим ключам;
- никаких `tos: avoid`, никаких подписок через OAuth;
- `openrouter/auto` запрещён;
- вход по паролю, порт только на `127.0.0.1`.

### 6.1 Установка (под пользователем `openclaw`)

У нас OmniRoute стоит в пользовательский префикс `~/.local`, не в системный:

```bash
npm install -g --prefix ~/.local omniroute@3.8.51     # или без версии — последняя
~/.local/bin/omniroute --version                       # 3.8.51
```

Установка на 1 ГБ идёт около 6 минут. Предупреждения `npm warn ERESOLVE` безвредны (так сказано в README). Если npm пишет, что install-скрипты не разрешены (`allowScripts`), и `omniroute` потом не запускается, переустановите с флагом `--allow-scripts=…`: точный список пакетов npm печатает в том же предупреждении. У нас OmniRoute работает и без него.

Docker тоже возможен (`docker run … -p 127.0.0.1:20128:20128 …`, см. README), но на 1 ГБ мы его не ставили.

### 6.2 Файл окружения `~/.omniroute/.env`

Шаблон: [files/omniroute.env.example](files/omniroute.env.example).

```bash
mkdir -p ~/.omniroute && chmod 700 ~/.omniroute
cat > ~/.omniroute/.env <<EOT
PORT=20128
OMNIROUTE_SERVER_HOST=127.0.0.1
DATA_DIR=$HOME/.omniroute
INITIAL_PASSWORD=$(openssl rand -base64 18)
JWT_SECRET=$(openssl rand -base64 48)
API_KEY_SECRET=$(openssl rand -hex 32)
STORAGE_ENCRYPTION_KEY=$(openssl rand -hex 32)
REQUIRE_API_KEY=true
OMNIROUTE_MEMORY_MB=448
EOT
chmod 600 ~/.omniroute/.env
grep INITIAL_PASSWORD ~/.omniroute/.env    # запишите пароль дашборда в менеджер паролей
```

- `OMNIROUTE_SERVER_HOST=127.0.0.1` — слушать только локально.
- `REQUIRE_API_KEY=true` — без ключа API не пускает.
- `OMNIROUTE_MEMORY_MB=448` — потолок кучи Node. По `.env.example` его надо задавать явно, если память ограничена.

При запуске OmniRoute может предупредить, что переменные из `.env` внутри пакета игнорируются. Это нормально: побеждает ваш `~/.omniroute/.env`.

### 6.3 Служба systemd с лимитами памяти

Файл `~/.config/systemd/user/omniroute.service` (копия: [files/omniroute.service](files/omniroute.service)):

```ini
[Unit]
Description=OmniRoute AI gateway (loopback only)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/.omniroute
EnvironmentFile=%h/.omniroute/.env
Environment=NODE_ENV=production
ExecStart=%h/.local/bin/omniroute serve --no-open --no-tray --ready-timeout 240000 --port 20128
Restart=on-failure
RestartSec=20
OOMScoreAdjust=900
MemoryHigh=450M
MemoryMax=650M
MemorySwapMax=600M

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now omniroute
systemctl --user status omniroute
```

- `OOMScoreAdjust=900`: если память кончится, ядро первым убьёт OmniRoute, а не шлюз OpenClaw. OpenClaw тогда просто уйдёт на запасные модели.
- `MemoryMax=650M` ограничивает саму службу.
- `--ready-timeout 240000`: на медленном сервере старт занимает минуты.

### 6.4 Дашборд, пароль и ключ для OpenClaw

Дашборд открыт только на сервере. С вашего компьютера к нему ходят через SSH-туннель:

```bash
ssh -L 20128:127.0.0.1:20128 openclaw@<SERVER_IP>
# в браузере: http://localhost:20128  (пароль — INITIAL_PASSWORD; смените в Settings → Security)
```

1. **Создайте API-ключ** для OpenClaw (в README он берётся в Dashboard → Endpoints / API Keys). Запишите его:
   ```bash
   read -rs K
   echo "OMNIROUTE_API_KEY=$K" >> ~/.openclaw/.env && chmod 600 ~/.openclaw/.env
   echo "OMNIROUTE_API_KEY=$K" >> ~/.omniroute/.env     # чтобы работали CLI и тест-скрипт
   unset K
   ```
2. **Настройки фильтров**: вход по паролю, скрыть платные модели, исключить `tos: avoid`, запретить `openrouter/auto`. Тело запроса: [files/omniroute-settings.json](files/omniroute-settings.json).
   ```json
   {
     "requireLogin": true,
     "hidePaidModels": true,
     "excludeTosAvoid": true,
     "modelVisibilityDenylist": ["openrouter/auto", "openrouter/stealth/ox-alpha"]
   }
   ```
   Применить можно тремя способами:
   - **CLI:** `omniroute api settings patch-api-settings --body @omniroute-settings.json`. Команда есть в `omniroute api settings --help`.
   - **Наш способ:** через вспомогательный скрипт [files/omniroute-mgmt.mjs](files/omniroute-mgmt.mjs), который ходит в локальный API с CLI-токеном OmniRoute. Скопируйте его в `~/.omniroute/mgmt.mjs` и выполните:
     ```bash
     node ~/.omniroute/mgmt.mjs PATCH /api/settings "$(cat omniroute-settings.json)"
     node ~/.omniroute/mgmt.mjs GET /api/settings | grep -o '"excludeTosAvoid":[a-z]*'
     ```
   - **Дашборд:** раздел Settings.

   Все эти ключи есть в схеме настроек OmniRoute (`settingsSchemas.ts`).

### 6.5 Провайдеры: только бесплатные, по ключам

```bash
export PATH=$HOME/.local/bin:$PATH
read -rs GEMINI_KEY; export GEMINI_KEY
omniroute providers add gemini --name gemini-free --credential-env GEMINI_KEY
read -rs GROQ_KEY;   export GROQ_KEY
omniroute providers add groq   --name groq-free   --credential-env GROQ_KEY
read -rs NVIDIA_KEY; export NVIDIA_KEY
omniroute providers add nvidia --name nvidia-free --credential-env NVIDIA_KEY
unset GEMINI_KEY GROQ_KEY NVIDIA_KEY

omniroute providers list
omniroute providers test-all
```

Что у нас в итоге:

- **Активны:** `gemini-free`, `groq-free`, `nvidia-free`.
- **Добавлены, но выключены:** `sambanova-free` (кредиты кончились, требует карту) и `mistral-free` (постоянные 429). Выключить можно так: `omniroute providers edit <имя> --inactive`.
- **OpenRouter в OmniRoute не подключён.** OmniRoute считает бесплатным платный `openrouter/auto` и мог бы тратить ваши кредиты. Бесплатные модели OpenRouter OpenClaw вызывает напрямую, мимо OmniRoute.
- **Не подключайте** Kiro, OpenCode Free (они помечены `tos: avoid`) и любые OAuth-подписки (`omniroute oauth …`, `providers add --oauth`).

Тест прямо через API, обычный ответ и вызов инструмента. Скрипт: [files/omniroute-test-models.mjs](files/omniroute-test-models.mjs). Он читает `OMNIROUTE_API_KEY` из `~/.openclaw/.env`.

```bash
node ~/.omniroute/test-models.mjs auto T:auto
```

---

## 7. Tailscale Serve и приложение на iPhone

### 7.1 Tailscale на сервере (или компьютере)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                       # откройте ссылку и войдите в свой аккаунт Tailscale
sudo tailscale set --operator=$USER     # чтобы шлюз мог управлять Serve без sudo (рекомендация docs.openclaw.ai)
tailscale status
```

В [админке Tailscale](https://login.tailscale.com/admin/dns) включите **MagicDNS** и **HTTPS Certificates**. Без HTTPS Serve не работает ([kb/1312/serve](https://tailscale.com/kb/1312/serve)). Если Serve на tailnet не включён, при старте шлюз напишет предупреждение со ссылкой для включения. Откройте её и затем выполните `openclaw gateway restart`.

В конфиге OpenClaw (уже есть во фрагменте [files/openclaw-gateway.json](files/openclaw-gateway.json)):

```json
{ "gateway": { "bind": "loopback", "port": 18789, "auth": { "mode": "token" }, "tailscale": { "mode": "serve" } } }
```

Шлюз сам поднимает Serve как «foreground claim», пока он запущен ([docs.openclaw.ai/gateway/tailscale](https://docs.openclaw.ai/gateway/tailscale)). Поэтому `tailscale serve status` может написать «No serve config»; смотрите `tailscale serve status --json`. Адрес шлюза получится такой: `wss://<TAILNET-HOST>.<TAILNET>.ts.net`.

### 7.2 Подключение iPhone

1. Поставьте на iPhone **Tailscale** и войдите **в тот же аккаунт**, затем включите VPN. Адрес `*.ts.net` доступен только внутри вашей сети Tailscale, поэтому Tailscale нужен даже при наличии приложения OpenClaw.
2. Поставьте приложение **OpenClaw** из App Store.
3. На сервере выполните:
   ```bash
   openclaw qr                 # QR-код в терминале
   openclaw qr --json          # или setupCode в JSON, если удобнее вставить текстом
   ```
4. В приложении отсканируйте QR или вставьте setup code. Официальное приложение подключается само. Если запрос завис:
   ```bash
   openclaw devices list
   openclaw devices approve <requestId>
   ```

Setup code короткоживущий и одноразовый. Не пересылайте его в чатах. Документация: [docs.openclaw.ai/cli/qr](https://docs.openclaw.ai/cli/qr).

---

## 8. Делегирование задач от других ботов

Идея в том, чтобы дорогой ИИ-ассистент (бот) отдавал «грязную» работу (поиск, черновики, скрипты) OpenClaw на бесплатных моделях, а потом выборочно проверял результат.

### 8.1 Ключ владельца

На машине, где живут ваши боты (например, отдельная Linux-машина):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/oc_owner -N "" -C oc-owner
ssh-copy-id -i ~/.ssh/oc_owner.pub openclaw@<SERVER_IP>      # или допишите .pub в ~/.ssh/authorized_keys сервера
ssh -i ~/.ssh/oc_owner openclaw@<SERVER_IP> 'openclaw --version'
```

Скрипты ожидают ключ именно по пути `~/.ssh/oc_owner`.

### 8.2 `oc-delegate`: отдать задачу и получить ответ

Исходник: [files/oc-delegate](files/oc-delegate). Установка на машину бота:

```bash
sed -i 's/<SERVER_IP>/203.0.113.10/' oc-delegate oc-mail   # ваш адрес вместо примера (или export OC_HOST=openclaw@<адрес>)
sudo install -m 755 oc-delegate oc-mail /usr/local/bin/
```

На сервер положите извлекатель ответа [files/ocx.py](files/ocx.py) в `~/bin/ocx.py`. Его использует `oc-gate`; `oc-delegate` владельца передаёт такой же код сам.

Использование:

```bash
oc-delegate "Reply with exactly: ok"                                  # агент main
oc-delegate --agent researcher --timeout 600 "Найди … дай 3 ссылки"   # исследователь
oc-delegate --agent worker "Напиши bash-скрипт, который …"           # исполнитель
J=$(oc-delegate --bg --agent researcher "долгая задача")              # в фоне → id задачи
oc-delegate --result "$J" --wait                                      # забрать результат
oc-delegate --jobs                                                    # список задач
```

Коды выхода: `0` — готово, `75` — ещё выполняется, остальное — ошибка (текст в stderr). Внутри скрипт вызывает на сервере `openclaw agent --agent … --session-key … --timeout … --json --message-file …` и вытаскивает из JSON только текст ответа. Задачи и ответы лежат в `~/oc-jobs/` на сервере.

Каждый вызов занимает от 25 секунд до 3 минут. Одновременно идёт не больше 2 задач.

### 8.3 Навык (skill) для ботов

Правила, когда делегировать и как проверять, лежат в [files/SKILL-owner.md](files/SKILL-owner.md). Сохраните его как навык `openclaw-delegate` у каждого своего бота. Кратко:

- **Отдаём:** самостоятельные задачи, где можно подождать (поиск с источниками, черновики, перевод, маленькие скрипты).
- **Не отдаём:** всё, что требует ваших аккаунтов, отправки сообщений, денег, удаления данных, секретов, а также срочное и крошечное.
- **Проверяем:** 1–2 ключевых факта, код запускаем, текст вычитываем. Если ответ плохой, повторяем один раз, иначе делаем сами.

### 8.4 Второй пользователь: ключ с forced command (`oc-gate`)

Второму пользователю (его агент на сервере — `guest`) владелец даёт SSH-ключ, который **не открывает shell**. Он запускает только скрипт [files/oc-gate](files/oc-gate). Тот принимает команды `run`, `result`, `jobs` (задачи агентам `guest`, `researcher`, `worker`) и `mail`, всё остальное отвергает. Агент `main` владельца ему недоступен.

На сервере:

```bash
mkdir -p ~/bin
install -m 755 oc-gate ~/bin/oc-gate
install -m 755 ocmail.py ~/bin/ocmail.py
install -m 644 ocx.py ~/bin/ocx.py
```

Ключ для второго пользователя генерируйте у себя, не на сервере:

```bash
ssh-keygen -t ed25519 -f oc_guest -N "" -C oc-guest
```

Добавьте в `~/.ssh/authorized_keys` на сервере **одну строку** (подставьте содержимое `oc_guest.pub`):

```text
command="/home/openclaw/bin/oc-gate",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-ed25519 <PUBLIC_KEY_OF_SECOND_USER> oc-guest
```

Отпечаток ключа сервера для пакета:

```bash
ssh-keyscan -t ed25519 <SERVER_IP> > known_hosts
ssh-keygen -lf known_hosts                 # SHA256:… → впишите в SETUP-guest.md вместо <HOST_KEY_FINGERPRINT>
```

Пакет для бота второго пользователя:

- `oc_guest` (приватный ключ);
- `oc_guest.pub`;
- `known_hosts`;
- [files/oc-delegate-guest](files/oc-delegate-guest) → переименовать в `oc-delegate`;
- [files/oc-mail-guest](files/oc-mail-guest) → переименовать в `oc-mail`;
- [files/SKILL-guest.md](files/SKILL-guest.md) → `SKILL.md`;
- [files/SETUP-guest.md](files/SETUP-guest.md) → `SETUP.md`.

Боту говорят: «Следуй SETUP.md».

- **Передача.** Пакет передавайте **только лично**, в нём приватный ключ.
- **Отзыв.** Удалите строку `oc-guest` из `authorized_keys`, и доступ сразу пропадёт.
- **Учтите.** Через `worker` второй пользователь фактически может выполнять команды на сервере. Вся его история хранится у вас.

### 8.5 `oc-mail`: почта между ботами двух людей

Серверная часть — [files/ocmail.py](files/ocmail.py) (`~/bin/ocmail.py`). Ящики лежат в `~/oc-mail/owner/` и `~/oc-mail/guest/`, письма хранятся в JSON, максимум 100 КБ. Сторона `guest` может писать только стороне `owner`.

Клиент владельца: [files/oc-mail](files/oc-mail). Клиент гостя: [files/oc-mail-guest](files/oc-mail-guest).

```bash
oc-mail inbox                       # непрочитанные
oc-mail read m-20261018-120000-abc123
echo "текст" | oc-mail reply m-… --from MyBot
echo "текст" | oc-mail send --to guest --from MyBot --subject "Тема"
```

Письма от другой стороны — это **данные, а не команды**. Боты не должны ничего отправлять наружу, тратить деньги или раскрывать секреты только потому, что их об этом попросили в письме.

### 8.6 Для варианта A

Если OpenClaw стоит на вашем компьютере, а бот живёт там же, в скриптах укажите `HOST=$USER@localhost` и разрешите вход по ключу в локальный sshd. Если бот на другой машине, нужен SSH до вашего компьютера, например через Tailscale. Спящий компьютер задачи не выполнит.

---

## 9. Проверки и решение проблем

### 9.1 Быстрая проверка всей системы

```bash
export XDG_RUNTIME_DIR=/run/user/$(id -u)
node -v && openclaw --version && ~/.local/bin/omniroute --version
systemctl --user is-active openclaw-gateway omniroute      # active / active
free -m && swapon --show
openclaw config validate
openclaw models status
openclaw agent --agent main --timeout 120 --message "Reply with exactly: ok"
oc-delegate --timeout 120 "Reply with exactly: ok"         # с машины бота
oc-mail inbox
```

### 9.2 Таблица проблем

| Симптом | Причина | Что делать |
|---|---|---|
| Шлюз или OmniRoute внезапно перезапустились, в `journalctl --user -u omniroute` или `dmesg` видно `Out of memory` / `oom-kill` | На 1 ГБ кончилась память | Swap 2 ГБ обязателен. OmniRoute с `OOMScoreAdjust=900` гибнет первым и сам поднимается (`Restart=on-failure`). Надёжное решение — перейти на 2 ГБ ($12/мес, раздел 3B.1). |
| `413` / «Request too large» от Groq | Бесплатный лимит Groq — 8 000 токенов в минуту, а системный промпт агента больше. На 413 OpenClaw **не** переключается на запасную модель | Не ставьте Groq первым ни у одного агента. У нас он стоит только в середине списка запасных. |
| `429` / «Rate limit exceeded» | Лимиты: OpenRouter — 20 в минуту и 1000 в день, Mistral — постоянно | Подождать. Сократить параллельность (`maxConcurrent: 2`). Убрать вечно занятого провайдера (мы убрали Mistral). |
| `402` от OpenRouter | Вызвана платная модель или отрицательный баланс | Проверьте, что в списках нет `openrouter/auto` и моделей без `:free` (кроме `openrouter/free`). |
| Ответ «ok» идёт 1–2 минуты, шлюз стартует ~2 минуты | Сервер свопит (1 ГБ) | Норма для 1 ГБ. Ускоряет переход на 2 ГБ. Смотрите `journalctl --user -u openclaw-gateway -f`. |
| Модель долго молчит (Nemotron, Nemotron Ultra) | Перегружен бесплатный пул | Её место в запасных. Главную держите на `omniroute/auto` и Inkling. |
| NVIDIA перестала отвечать | Кончились пробные кредиты | Сработают запасные. Уберите `nvidia/*` из списков и `nvidia-free` в OmniRoute. |
| Телефон не подключается | Tailscale на телефоне выключен или другой аккаунт; Serve не включён на tailnet; HTTPS выключен | Включите VPN Tailscale на iPhone, включите HTTPS и Serve в админке, выполните `openclaw gateway restart`, затем заново `openclaw qr`. |
| `systemctl --user` в SSH пишет «Failed to connect to bus» | Не задан `XDG_RUNTIME_DIR` | `export XDG_RUNTIME_DIR=/run/user/$(id -u)`; проверьте, что включён linger (`loginctl show-user openclaw` → `Linger=yes`). |
| `oc-delegate`: `ssh: command not found` (или раньше `sshpass: command not found`) | На машине бота пропал SSH-клиент | `sudo apt-get install -y openssh-client`. Наши скрипты пробуют поставить его сами и ходят по ключу, без `sshpass`. |
| `models scan` поставил крошечную модель по умолчанию | Скан выбирает по своим критериям | Задайте модели фрагментом из раздела 4. |

### 9.3 Откат

```bash
cd ~/.openclaw
ls -t openclaw.json.bak* | head          # ваши резервные копии
cp openclaw.json.bak-<дата> openclaw.json && chmod 600 openclaw.json
openclaw config validate && openclaw gateway restart
```

Отключить OmniRoute полностью:

```bash
systemctl --user disable --now omniroute
# главная модель снова Inkling:
jq -s '.[0] * .[1]' ~/.openclaw/openclaw.json ~/openclaw-no-omniroute.json > /tmp/oc.json \
  && install -m 600 /tmp/oc.json ~/.openclaw/openclaw.json && rm /tmp/oc.json
openclaw config validate && openclaw gateway restart
```

Резервная копия всего состояния: `openclaw backup --help` (создание и проверка архивов).

---

## 10. Безопасность

- **Только бесплатное.** Никаких платных моделей в списках. `openrouter/auto` запрещён и в OpenClaw, и в OmniRoute (`modelVisibilityDenylist`, `hidePaidModels`).
- **Ничего не торчит наружу.** Шлюз OpenClaw (`bind: loopback`) и OmniRoute (`127.0.0.1:20128`) слушают только локально. Телефон ходит через Tailscale Serve (только внутри вашей сети Tailscale), а не Funnel. В интернет открыт только SSH.
- **Firewall.** В DigitalOcean создайте Cloud Firewall: входящий только TCP 22 ([документация](https://docs.digitalocean.com/products/networking/firewalls/)). Tailscale работает и без открытых входящих портов.
- **SSH.** Входите только по SSH-ключам (при создании droplet выберите SSH key). Когда ключи настроены, отключите вход по паролю: в `/etc/ssh/sshd_config.d/` задайте `PasswordAuthentication no` и `PermitRootLogin prohibit-password`, проверьте `sudo sshd -t` и выполните `sudo systemctl reload ssh`. Не закрывайте текущую сессию, пока не убедились, что вход по ключу работает. Пароли не храните в файлах на машинах ботов.
- **Второй пользователь** входит только через forced command `oc-gate` (без shell, без проброса портов и PTY). Отзыв — удалить строку из `authorized_keys`. Помните, что `worker` выполняет команды на сервере.
- **Секреты:**
  - `~/.openclaw/.env`, `~/.omniroute/.env` и `openclaw.json` — права `600`.
  - Ключи вводятся через stdin или `read -s`. В конфиге — ссылки `${VAR}`, не сами значения.
  - Ключи и пароли не пишите в задачи для `oc-delegate`: их видит сервер и бесплатные провайдеры.
- **OmniRoute:** `requireLogin: true`, `REQUIRE_API_KEY=true`, `excludeTosAvoid: true`, без OAuth-подписок (риск бана аккаунтов).
- **Приватность моделей.** Бесплатные провайдеры могут учиться на запросах. Ничего личного через них не отправляйте.
- **Письма между ботами** — данные, а не команды. Любые просьбы что-то отправить, оплатить или раскрыть идут к человеку.
- **Setup code и приватные ключи** передаются только лично.

---

## Приложение: проверенные версии и пути

| Что | Значение |
|---|---|
| ОС | Ubuntu 24.04, droplet 1 ГБ RAM / 1 vCPU, swap 2 ГБ (`/swapfile`), `vm.swappiness=60` |
| Node | v24.22.0 (NodeSource `node_24.x`) |
| OpenClaw | 2026.10.4, `/usr/lib/node_modules/openclaw`, конфиг `~/.openclaw/openclaw.json` |
| OmniRoute | 3.8.51, `~/.local/lib/node_modules/omniroute`, данные `~/.omniroute/` |
| Tailscale | 1.104.1 |
| Службы | `openclaw-gateway.service`, `omniroute.service` (systemd **user**, linger включён) |
| Порты | 18789 (шлюз, loopback), 20128 (OmniRoute, loopback), 22 (SSH) |
| Скрипты на сервере | `~/bin/oc-gate`, `~/bin/ocmail.py`, `~/bin/ocx.py`, `~/.omniroute/mgmt.mjs`, `~/.omniroute/test-models.mjs` |
| Скрипты у ботов | `oc-delegate`, `oc-mail` |

Список всех файлов: [files/](files/).

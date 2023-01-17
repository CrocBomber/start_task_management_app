# Management приложение

Приложение увеличивает или уменьшает количество нод основного приложения в зависимости от нагрузки на текущие ноды.
Работает на порту 80.
Реализовано в виде systemd службы.
Максимальное количество нод ограничивается в конфиге параметром node_limit и по умолчанию составляет 4.
Приложение отслеживает экземпляры с тегом cpu bound, имя тега можно изменить через параметр watched_app_tag.
При необходимости приложение создаёт новый экземпляр из шаблона с именем cpu_bound. Имя шаблона меняется через параметр template_name.
Инструкция по подготовке шаблона основного приложения находится в репозитории с основным приложением.
Приложение ожидает порт основного приложения 5000, и он меняется через параметр application_port.
При создании нового экземпляра из шаблона создаётся новый аларм для CPU Utilization > 70%
Имя аларма начинается с префикса cpu_bound_cpu_utilization_. По этому же префиксу проверяется состояние алармов запущенных машин.
Префикс аларма меняется через параметр alarm_name_prefix.


## Инструкция по деплою и тестированию данного приложения.

1. Импортировать публичный SSH-ключ
2. В группах безопасности открыть входящие TCP порты как минимум: 22, 80
3. Создать Elastic-IP.
4. Создать новый экземпляр виртуальной машины Ubuntu 22.04 [Cloud Image]
Тип машины: m5.large
Тег Name: load balancer
Количество экземпляров: 1
Elastic IP: выбрать автоматически
5. Залогиниться по внешнему IP адресу по SSH используя импортированный ключ и имя пользователя ec2-user.
6. Выполнить sudo apt update
7. Поставить пакеты python3-venv и python3-pip
8. Создать каталог ~/dev/croc: mkdir -p ~/dev/croc
9. Перейти в каталог ~/dev/croc и склонировать этот репозиторий: git clone git@github.com:CrocBomber/start_task_management_app.git
10. Перейти в каталог со склонированым репозиторием: cd start_task_management_app
11. Создать виртуальное окружение командой: python3 -m venv .venv
12. Активировать виртуальное окружение командой: . .venv/bin/activate
13. Установить зависимости командой: pip install -r requirements.txt
14. Скопировать файл template.main.ini с новым именем main.ini: cp template.main.ini main.ini
15. Отредактировать файл main.ini указав актуальные параметры. Как минимум subnet_id должен указывать на нужную подсеть в облаке.
16. Скопировать файл template.cloud.ini с новым именем cloud.ini: cp template.cloud.ini cloud.ini
17. Отредактировать файл cloud.ini прописав актуальные значения для aws_access_key_id и aws_secret_access_key для доступа к облаку.
18. Скопировать файл template.nginx.conf с новым именем nginx.conf: cp template.nginx.conf nginx.conf
19. Отредактировать файл nginx.conf поменяв в строке server %FIRST_HOST%; значение %FIRST_HOST% на хост и порт существующего основного приложения в формате хост:порт (без http://)
Если хостов нету, то удалить эту строку. Если хостов несколько, то размножить строку в соответствии с количеством хостов.
20. Установить пакет nginx
21. Добавить для пользователя ec2-user возможность перечтения конфигов без ввода sudo пароля:
Открыть на редактирование файл командой: sudo visudo -f /etc/sudoers.d/nginx_service
Добавить строку: ec2-user ALL = NOPASSWD: /usr/bin/systemctl reload nginx.service
Сохранить файл.
Это строка даст возможность пользователю ec2-user перечитывать конфиги nginx без запроса пароля.
22. Удалить дефолтный сервис из nginx sudo unlink /etc/nginx/sites-enabled/default 
23. Добавить конфиг в nignx командой: sudo ln -s /home/ec2-user/dev/start_task_management_app/nginx.conf /etc/nginx/sites-available/
24. Сделать его активным: sudo ln -s /etc/nginx/sites-available/nginx.conf /etc/nginx/sites-enabled/
25. Перечитать конфиги sudo systemctl reload nginx.service
26. Скопировать файл template.management_app.service с новым именем management_app.service: cp template.management_app.service management_app.service
27. Отредактировать файл:
Найти подстроки %APP_DIR% и заменить на /home/ec2-user/dev/start_task_management_app
Найти подстроку %PYTHON_PATH% и заменить на /home/ec2-user/dev/start_task_management_app/.venv/bin/python3
28. Добавить службу в systemd командой: sudo ln -s /home/ec2-user/dev/start_task_management_app/management_app.service /etc/systemd/system/
29. Активировать службу командой: sudo systemctl enable management_app.service
30. Запустить службу командой: sudo systemctl start management_app.service
31. Проверить статус службы, что нету ошибок: sudo systemctl status management_app.service
32. Смотреть логи службы можно командой: tail -f -n 200 /var/log/management_app.log
33. Зайти на сервис через браузер для проверки работоспособности


# Тестирование работоспособности

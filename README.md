# Management приложение

Приложение увеличивает или уменьшает количество нод основного приложения в зависимости от нагрузки на текущие ноды.
Работает на порту 80.
Реализовано в виде systemd службы.


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
14. Скопировать файл template.config.ini с новым именем config.ini: cp template.config.ini config.ini
15. Отредактировать файл config.ini прописав актуальные значения для aws_access_key_id и aws_secret_access_key для доступа к облаку.
16. Скопировать файл template.nginx.conf с новым именем nginx.conf: cp template.nginx.conf nginx.conf
17. Отредактировать файл nginx.conf поменяв в строке server %FIRST_HOST%; значение %FIRST_HOST% на хост и порт существующего основного приложения в формате хост:порт (без http://)
Если хостов нету, то удалить эту строку. Если хостов несколько, то размножить строку в соответствии с количеством хостов.
18. Установить пакет nginx
19. Добавить для пользователя ec2-user возможность перечтения конфигов без ввода sudo пароля:
Открыть на редактирование файл командой: sudo visudo -f /etc/sudoers.d/nginx_service
Добавить строку: ec2-user ALL = NOPASSWD: /usr/bin/systemctl reload nginx.service
Сохранить файл.
Это строка даст возможность пользователю ec2-user перечитывать конфиги nginx без запроса пароля.
20. Удалить дефолтный сервис из nginx sudo unlink /etc/nginx/sites-enabled/default 
21. Добавить конфиг в nignx командой: sudo ln -s /home/ec2-user/dev/start_task_management_app/nginx.conf /etc/nginx/sites-available/
22. Сделать его активным: sudo ln -s /etc/nginx/sites-available/nginx.conf /etc/nginx/sites-enabled/
23. Перечитать конфиги sudo systemctl reload nginx.service
24. Скопировать файл template.management_app.service с новым именем management_app.service: cp template.management_app.service management_app.service
25. Отредактировать файл:
Найти подстроки %APP_DIR% и заменить на /home/ec2-user/dev/start_task_management_app
Найти подстроку %PYTHON_PATH% и заменить на /home/ec2-user/dev/start_task_management_app/.venv/bin/python3
26. Добавить службу в systemd командой: sudo ln -s /home/ec2-user/dev/start_task_management_app/management_app.service /etc/systemd/system/
27. Активировать службу командой: sudo systemctl enable management_app.service
28. Запустить службу командой: sudo systemctl start management_app.service
29. Проверить статус службы, что нету ошибок: sudo systemctl status management_app.service
30. Смотреть логи службы можно командой: tail -f -n 200 /var/log/management_app.log
31. Зайти на сервис через браузер для проверки работоспособности


# Тестирование работоспособности

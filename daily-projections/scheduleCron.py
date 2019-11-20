from crontab import CronTab

my_cron = CronTab(user='matt')

job = my_cron.new(command = '~/Documents/GitHub/Ottoneu/venv/bin/python ~/Documents/GitHub/Ottoneu/daily-projections/PointProj.py')

job.setall('0 8 * * *')

my_cron.write()

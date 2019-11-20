from crontab import CronTab

my_cron = CronTab(user='matt')

job = my_cron.new(command = '~/Google\ Drive/Carleton/Junior\ Year/Fantasy/venv/bin/python ~/Google\ Drive/Carleton/Junior\ Year/Fantasy/PointProj.py')

job.setall('0 8 * * *')

my_cron.write()

from cyst.api.environment.environment import Environment

e = Environment.create()
e.control.init()
e.control.run()
e.control.commit()

stats = e.infrastructure.statistics

print(f"Run id: {stats.run_id}\nStart time real: {stats.start_time_real}\n"
      f"End time real: {stats.end_time_real}\nDuration virtual: {stats.end_time_virtual}")

all:
	cd testgame; PYTHONPATH=.. python startgame.py

api:
	rm -rf ../doc/api
	mkdir ../doc/api
	epydoc -vo ../doc/api --no-frames --no-private --exclude=parole.config --name="Python Advanced Roguelike Engine: API Documentation" parole

apicheck:
	epydoc -vo ../doc/api --no-private --exclude=parole.config --check parole


# Objective
The main objective of this project is to provide easy breakdowns of my finances by allowing me to upload pictures of myreceipts and store that data in a uniform way. Using graphs and tables to understand how my money is being spent.

Later down the line we can incorporate E-Receipts in email and Banking APIs, but for now what we want is to only have physical receipt upload tracking.

## Tech Stack
- Ubuntu Server
- Docker
- OCR Model
- Next.Js Frontend
- Model for Categorizing Places (Or LLM For starting)

## Implementation Plan
I plan on first finding a model that is free and lightweight that has a good consistency of being able to read text from a picture. (easyocr Python lib)

Then once we have that we can containerize the model and setup an API to allow images to be passed through.

Once the OCR model is setup then I can link the cheapest LLM or Create my own category predective model, allowing me to properly categorize my spending habits.

Once we have the API setup then we can setup an nginx container on an ubuntu server and create a data schema so that we are categorizing data in a proper fashion.

### How to Find the expense
After extracting all of the text from the model, all we need to do is run a string search for any number next to the word "Total" or any of it's variations, then convert the nums to ints, then run a comparison operation.


### Current Impementation Notes
Currently I have implemented the most basic of string manipulation to get the total from a receipt. These receipts are tested from 3 different walmart receipts stored on my machine. 

The next step in the process is to now figure out a way for this to run continuosly, be able to pass an image into it and it spit out the number.

To do this I want to put it into a container, the container is waiting for incoming pictures and once it has processed and sent the receiver the number it stays up and running. I will have to install docker for this and then I will have to think about how I want to do this, maybe run a fastapi middleware or an express.js middleware. FastAPI might be the move only because it will stay in theme with the python code but I am more familiar with express.js, I'll think about it. But for now I'll go ahead and install docker and start working on my own container.

I have now put together the container, setup a fastapi middleware to handle incoming images, and made the ocr model easy to use behind the middleware.

So now that we have that all setup in a docker container we need to somehow make it so that when images are sent we store the images and put the costs with them. There are a few ways that we can go about it but the idea that is popping up into my mind now is we put another layer of middleware to handle all incoming reqs, once the images are sent we send it to the fast api middleware and then we return the image and the cost from the fastapi to the middleware so that the middleware can then send the newe json package of the image with the cost to the database. 

That's the overall goal for my next steps.

After a lot of trial and tribulation I was able to get the middleware container to send the image to the backend container. I was able to do this by using the request library in python, I was just running into a stupid error of not naming a json object properly so the backend container was getting confused on all the informatino I was sending its way. But now everything is working as it should.

The only current improvements I plan to add today are having the image be removed from the container once it is done being processed just so that the containers don't get bloated. Then I'm going to attatch docker db, I'm thinking of using psql because I've really only had experience with firestore db. I want to stop being so locked in on one technology.

What the db is going to do is once the image has been processed in the backend and returned to the middleware, the middleware will send the information to be stored in the db. For now I don't plan on storing anything crazy, because all I'm testing is walmart receipts currently. But I'll make a basic table and see where it goes. 

I eventually plan to add some improvements to the processing in the backend so we can start grouping some categories such as grocery, automobile, recreation, other, etc.. The way I'm planning on doing that is using fuzzy string matching and regex in the backend just so we can group categories better and the frontend will have a wider variety of data to play around with. 

Before I ended up adding the psql container I just wanted to play around a bit so I created a compose.yaml file. Defintley a lot simpler than I initially thought it would be, but it is pretty awesome to see it work just so effortlesly. So just a small push before I add the db container.

Alright so I finally got data to persist through the freaking psql docker image, unfortunatley I seem to be horrible at reading documentation because there is a specific area in the docker container itself where data is stored. I have now fixed the point where the volume in the docker compose file writes data to. 

So now we don't have to worry about losing data if the image goes up or down, just don't let your data get corrupted lol

Anyways now that that's done, I've also been playing around with the psycopg library so that I can communicate with the psql container and I got that working a little while ago. I just need to go ahead and write some functions for this so that everything is standardized. I guess I should probably add a primary key to the data as well, just been a minute since I've messed around with SQL type dbs. But I'll figure this out, I mean this data isn't even that complicated it's just numbers we will be storing with D/T amd the type of expense it is.

Oooo I also keep forgetting I need to make a couple of different dicts so that I can start to hammer down on what goes where for grocery and stuff. In the front end I'll probably make it so that you can hard overide it just incase the OCR model fricks up cause it is not the best one in the world. Good enough for this though. 


  Summary:

  - Added FastAPI username/password auth with bcrypt password hashing.
  - Added database-backed opaque sessions:
      - New sessions SQLAlchemy model.
      - New Alembic migration 20260512_0002_add_sessions.py.
      - Session cookies are HTTP-only.
      - Logout revokes DB session and clears cookie.
  - Added auth endpoints:
      - POST /auth/register
      - POST /auth/login
      - POST /auth/logout
      - GET /auth/me
  - Added get_current_user dependency.
  - Protected receipt and integration routes.
  - Replaced the old default dev-user receipt upload behavior with authenticated ownership.
  - Added basic in-memory login rate limiting.
  - Added CORS config for http://localhost:3000.
  - Added backend auth tests and updated receipt upload tests.
  - Removed the now-unused informationHandler/app/dependencies.py.

  Frontend:

  - Created new web/ Next.js TypeScript app.
  - Added:
      - /login
      - /register
      - protected /dashboard
      - logout button
      - browser/server API helpers
      - proxy.ts route protection
  - Added web service to compose.yaml.
  - Verified npm run build passes.

  Docker/runtime fixes:

  - Original browser error was Failed to fetch because the API was not reachable.
  - Root cause: Postgres was crash-looping.
  - Postgres crash was caused by postgres:latest pulling PostgreSQL 18 against an
    incompatible/partial local volume.
  - Pinned database image to postgres:17.
  - Added .env.example.
  - Added missing local .env auth values:
      - SESSION_SECRET
      - MAX_UPLOAD_MB
      - COOKIE_SECURE
      - COOKIE_SAMESITE
      - FRONTEND_ORIGIN
  - Reset local Docker volumes with docker compose down -v.
  - Rebuilt and restarted the stack.
  - Ran migrations with:

    docker compose exec api alembic -c alembic.ini upgrade head

  - Verified:
      - curl http://localhost:8000/health
      - CORS preflight from http://localhost:3000
      - POST /auth/register returns 200 OK and sets receipt_tracker_session.

  Current run state:

  - Web: http://localhost:3000
  - API: http://localhost:8000
  - OCR: internal only
  - DB: internal only

  Verification commands that passed:

  PYTHONPATH=imageContainer ./.venv/bin/python -m pytest imageContainer/tests -q
  # 5 passed

  PYTHONPATH=informationHandler ./.venv/bin/python -m pytest informationHandler/tests -q
  # 9 passed

  cd web && npm run build
  # passed

  Important note:

  - I registered a test user during endpoint verification:
      - username: testuser
      - email: testuser@example.com
  - Use a different username/email, or reset volumes again if you want a clean DB.
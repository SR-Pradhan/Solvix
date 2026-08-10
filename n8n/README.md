# n8n workflows

Scheduled work lives here rather than inside the API, because the API sleeps
when idle — an in-process timer would only fire while someone happened to be
using the app, which is exactly when a reminder is least needed.

The split is deliberate: **n8n decides *when*, Solvix decides *what*.** Every
workflow in this folder calls an endpoint and moves the result around. None of
them contain product logic, so swapping n8n for anything else changes no
behaviour.

The JSON is kept in the repository so the automation is reviewable alongside
the code it drives, instead of existing only inside a hosted dashboard.

## daily-reminders.json

Every morning at 08:00 IST: ask Solvix what is due, then email each person who
has something.

```
Schedule → POST /jobs/daily-reminders?deliver=false → split messages → send email
```

`deliver=false` returns the composed emails instead of sending them. Render's
free instances block outbound SMTP entirely, so mail cannot leave the API; n8n
can reach a mail server, so it does the delivering. The wording is still built
and tested in `reminder_mail.py` — only the envelope moves.

### Importing it

1. n8n → **Workflows → Import from File** → this file.
2. Create two credentials:
   - **Header Auth** — name `X-Cron-Key`, value the `CRON_KEY` from Render.
     Attach it to *Ask Solvix what is due*.
   - **SMTP** — `smtp.gmail.com`, port 587, your sending address and its Gmail
     app password. Attach it to *Send it*, and set the same address as the
     sender.
3. Run it once by hand, then activate it.

The HTTP node retries three times, twenty seconds apart: the first call of the
day wakes a sleeping instance, which takes about fifty seconds.

Nobody with nothing due receives anything — an empty list produces no items to
send. A daily email that often says "nothing today" teaches its reader to
ignore it.

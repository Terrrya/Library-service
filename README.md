# Cinema API
<hr>

API service for library management writen on DRF. This service can managing books, borrows, payments, users 
authentication and registration. If book will borrow book's inventory will decrease and when it will return its 
inventory will increase. The book can not be borrowed when its inventory is 0. When client borrowing a book the payment 
will be created also. Another book can not be borrowed until client's payment was paid. Client can see only his borrows 
and payments, but staff user can see all payments and borrows. User can register himself and use library service, but 
books can see even unauthenticated users.  When new borrowing created or successful payment staff get message via Telegram.
Also, every day staff get a message about borrowing overdue and every minutes service will check the payments status

## Features:
<hr>

- JWT authenticated:
- Admin panel: /admin/
- Documentation is located at: /api/doc/swagger/
- Managing books and borrows
- Managing authentication & user registration
- Managing users' borrowings of books
- Notifications about new borrowing created, borrowings overdue & successful payment via Telegram
- Perform payments for book borrowings through the Stripe platform
- Filtering borrows

## Installing using GitHub
<hr>

Python3 should be installed

```python
git clone https://github.com/Terrrya/Library-service.git
cd Library-service
python3 -m venv venv
source venv/bin/activate
```
Create in root directory of project and fill .env file as shown in .env_sample file

```python
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

in next terminal

```python
python manage.py qcluster
```

in next terminal

```python
python manage.py t_bot
```
Open in browser 127.0.0.1:8000/api/

## Run with docker
<hr>

Docker should be installed

```python
git clone https://github.com/Terrrya/Library-service.git
cd Library-service
```

Create in root directory of project and fill .env file as shown in .env_sample file

```python
docker compose up
```
Open in browser 127.0.0.1:8000/api/ 

## Filling .env file
<hr>

To fill .env file you have to get API token of telegram bot and Stripe Secret API Token. 
<br> https://core.telegram.org/bots/faq#how-do-i-create-a-bot can help you to get Telegram API token
<br> https://stripe.com/docs/keys - can help you to get Stripe secret access key


## Getting access
<hr>

You can use following:
- superuser:
  - Email: admin@admin.com
  - Password: 12345
- user:
  - Email: test@library.com
  - Password: test12345

Or create another one by yourself:
- create user via api/user/register/

To work with API library token use:
- get access token and refresh token via api/user/token/
- verify access token via api/user/token/verify/
- refresh access token via api/user/token/refresh/


### Note: **Make sure to send Token in api urls in Headers as follows**

```
key: Authorize
value: Bearer <token>
```

### Telegram notification
If you want to get messages from your telegram bot you should write to your bot "/start". 
If you want to stop it you should write "/stop". A few staffs can get notifications, not only one.

## Library API allows:

- via api/admin/ --- Work with admin panel
- via /api/doc/swagger/ --- Detail api documentation by swagger
- via [POST] /api/user/register/ --- Register a new user
- via [POST] /api/user/token/ --- Obtain new Access and Refresh tokens via credential
- via [POST] /api/user/token/refresh/ --- Obtain new Access token via refresh token
- via [POST] /api/user/token/verify/ --- Verify Access token
- via [PUT, PATCH] /api/user/me/ --- Update user information
- via [POST] /api/books/ --- Add new book, only staff user can do it
- via [GET] /api/books/ --- Books list
- via [GET] /api/books/pk/ --- Book detail information
- via [PUT, PATCH] /api/books/pk/ --- Update book information, only staff user can do it
- via [DELETE] /api/books/pk/ --- Delete book, only staff user can do it
- via [GET] /api/borrows/ --- Borrows list
- via [POST] /api/borrows/ --- Add new borrow
- via [GET] /api/borrows/pk/ --- Borrow detail information
- via [POST] /api/borrows/pk/return/ --- Close borrow and return book to library
- via [GET] /api/payments/ --- Payments list
- via [GET] /api/payments/pk/ --- Payments detail information
- via [GET] /api/payments/pk/cancel_payment/ --- Display message to user about payment's possibilities and duration session
- via [GET] /api/payments/pk/is_success/ --- Check session's payment status
- via [GET] /api/payments/pk/renew_payment/ --- Renew payment

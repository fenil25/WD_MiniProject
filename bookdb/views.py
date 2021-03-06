from django.shortcuts import render, redirect
from .models import *
from django.db.models import Max, Avg
from django.contrib.auth import login, authenticate
import random
from recombee_api_client.api_client import RecombeeClient
from recombee_api_client.exceptions import APIException
from recombee_api_client.api_requests import *
from django.contrib.auth import logout

client = RecombeeClient('wd-project', 'DDf4VljyLxNsbdLtWT1jueFbVsanOWCwbEW59cTpp1W3LB3JlpeT3jqZQ1k7S7sN')

def searchBook(request):
	if request.method == 'GET':
		return render(request, 'bookdb/search.html', {})

def home(request):
	return render(request, 'index.html', {})

def user_logout(request):
    logout(request)
    return redirect('bookdb:home')

def login_or_register(request):
	if request.method == 'POST':
		data = request.POST
		if data.get('flag', '') == 'register':
			uid = User.objects.aggregate(Max('id'))['id__max'] + 1
			username = data.get('username', '')
			# [TODO] show an appropriate error message in case of same username
			if username == '' or User.objects.filter(username=username).count() > 0:
				return render(request, 'index.html', {'error': 'Repeated username'})
			user = User(id=uid)
			user.username = username
			user.set_password(data.get('password', ''))
			user.first_name = data.get('first_name', '')
			user.last_name = data.get('last_name', '')
			user.save()
			profile = UserProfile(user=user)
			profile.photo = request.FILES.get('photo', '')
			profile.save()
			login(request, user)
			return redirect('bookdb:home')
		elif data.get('flag', '') == 'login':
			username = data.get('username', '')
			password = data.get('password', '')
			user = authenticate(request, username=username, password=password)
			if user is not None:
				login(request, user)
				return redirect('bookdb:home')
			else:
				return render(request, 'bookdb/index.html', {'error': 'Incorrect username or password'})
	else:
		print("HIII")
		user = request.user
		list_of_isbns = []
		if not user.is_authenticated:
			# TODO: return some random isbn numbers here
			list_of_books = Book.objects.all().order_by("?")[:10]

			for book in list_of_books:
				list_of_isbns.append(book.isbn)
			print(list_of_isbns)
			return render(request, 'bookdb/index.html', {'recommended': list_of_isbns})
		else:
			# TODO: return some specific recommendations here
			recommended = client.send(RecommendItemsToUser(str(user.id), 10, cascade_create=True))
			for r in recommended['recomms']:
				list_of_isbns.append(r.get('id',''))
			print(list_of_isbns)
			return render(request, 'bookdb/index.html', {'recommended': list_of_isbns})

def book_detail(request, isbn):
	print(1)
	if not request.user.is_authenticated:
		print(2)
		return redirect('bookdb:home')
	try:
		print(3)
		print(isbn)
		book, created = Book.objects.get_or_create(isbn=isbn)
		print(4)
		comments = Comment.objects.filter(book=book).order_by('-time_of_comment')
		print(5)
		avg_rating = Rating.objects.filter(book=book).aggregate(Avg('rating')).get('rating__avg', 0)
		print(6)
		similar_books = [x.get('id', '') for x in client.send(RecommendItemsToItem(isbn, None, 10, cascade_create=True))['recomms']]
		print("s"*100)
		print(similar_books)
		return render(request, 'bookdb/book_detail.html', {'isbn': isbn, 'comments': comments, 'avg_rating': avg_rating, 'similar': similar_books})
	except Exception as e:
		print(7)
		print(e)
	print(8)
	return redirect('bookdb:home')

def rate_book(request, isbn):
	if not request.user.is_authenticated:
		return redirect('bookdb:home')
	if request.method == 'GET':
		return redirect('bookdb:book_detail', isbn=isbn)
	try:
		book = Book.objects.get(isbn=isbn)
		r = request.POST.get('rating', 0)
		profile = request.user.profile.first()
		rating, created = Rating.objects.get_or_create(user=profile, book=book)
		rating.rating = r
		rating.save()

		try:
			client.send(AddRating(str(request.user.id), isbn, (int(r)-5)/5, cascade_create=True))
		except APIException as e:
			print(e)

		return redirect('bookdb:book_detail', isbn=isbn)
	except Exception as e:
		print(e)
	return redirect('bookdb:home')

def comment(request, isbn):
	if not request.user.is_authenticated:
		return redirect('bookdb:home')
	if request.method == 'GET':
		return redirect('bookdb:book_detail', isbn=isbn)
	try:
		book = Book.objects.get(isbn=isbn)
		text = request.POST.get('text', '')
		profile = request.user.profile.first()
		print("Profile", profile)
		comment, created = Comment.objects.get_or_create(user=profile, book=book)
		comment.text = text
		comment.save()
		return redirect('bookdb:book_detail', isbn=isbn)
	except Exception as e:
		print("bd"*100)
		print(e)
	return redirect('bookdb:home')

def dashboard(request):
	if not request.user.is_authenticated:
		return redirect('bookdb:home')
	try:
		user = request.user
		profile = user.profile.first()
		recommended = client.send(RecommendItemsToUser(user.id, 10, cascade_create=True))
		recommendations = []
		for r in recommended['recomms']:
			recommendations.append(r.get('id',''))
		comments = profile.user_comments.all().order_by('-time_of_comment')
		ratings = profile.user_ratings.all()
		return render(request, 'bookdb/dashboard.html', {'profile': profile, 'recommendations': recommendations, 'comments': comments, 'ratings': ratings})
	except Exception as e:
		print(e)
	return render('bookdb:home')

from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from restaurant_admin.models import Restaurant, Menu, MenuItem
from .models import Cart, MenuItemCounter
from restaurant_admin.models import Restaurant
from .forms import CustomOrderForm, CustomTipForm, EmailForm, FeedbackForm
import stripe
import os
from decimal import Decimal
from django.contrib import messages
from django.core import serializers
from kitchen.models import OrderTracker


#this method is only for development, it shows all the menus you have on your local db
def show_all_menus(request):
    menus = Menu.objects.all()
    return render(request, 'customers/all_menus.html', {'menus': menus})


#this method just creates a cart object and then redirects to the menu
#method needs to be a post, otherwise someone could accidentally create 2 carts
def create_cart(request, restaurant_id, menu_id):
    if request.method == 'GET':
        cart = Cart()
        cart.restaurant = Restaurant.objects.filter(id = restaurant_id).first()
        cart.total = 0
        cart.total_with_tip = 0
        cart.save()
        cart.cash_code = 'QR' + str(cart.id)
        cart.save()
        #redirect to view menu page
        return redirect('/customers/view_menu/{cart_id}/{rest_id}/{m_id}'.format(cart_id = cart.id, rest_id = restaurant_id, m_id = menu_id))
    #otherwise it sends you to the page w/ all the menus
    else:
        return redirect('/customers')

'''Displays restaurant's menu'''
def view_menu(request, cart_id, restaurant_id, menu_id):
    if request.method == 'GET':
        curr_cart = Cart.objects.get(id = cart_id)
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        items = MenuItem.objects.filter(menu = curr_menu)
        return render(request, 'customers/menu.html', {'items': items, 'restaurant': curr_rest, 'cart': curr_cart, 'menu': curr_menu})
    else:
        return redirect('/customers/view_menu/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))

'''Renders About page for restaurants'''
def about_page(request, cart_id, restaurant_id, menu_id):
    if request.method == 'GET':
        curr_cart = Cart.objects.get(id = cart_id)
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        return render(request, 'customers/about.html', {'restaurant': curr_rest, 'cart': curr_cart, 'menu': curr_menu})
    else:
        return redirect('/customers/about/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))


""" for this template, make sure the item has a button to add to the cart, with a specified quantity,
send the item and specified quantity to the add_item url"""
def view_item(request, cart_id, restaurant_id, menu_id, item_id):
    if request.method == 'GET':
        form = CustomOrderForm()
        item = MenuItem.objects.filter(id = item_id).first()
        curr_cart = Cart.objects.get(id = cart_id)
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        return render(request, 'customers/view_item.html', {'item': item, 'cart': curr_cart, 'restaurant': curr_rest, 'menu': curr_menu, 'form':form})
    else:
        #if method is a post, then just redirect to this page as a get
        return redirect('/customers/view_item/{c_id}/{r_id}/{m_id}/{i_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id, i_id = item_id))


""" this method will add a new item to a cart if the cart didnt already contain the item,
otherwise it will increase/decrease the quantity of an item in a cart
this method expects a POST request to contain the quantity of the item being added to the cart
it also changes the total price of a cart accordingly"""
def add_item(request, cart_id, restaurant_id, menu_id, item_id):
    if request.method == 'POST':
        curr_cart = Cart.objects.filter(id = cart_id).first()
        curr_item = MenuItem.objects.filter(id = item_id).first()

        if request.POST['custom_instructions'] == '':
            item_counters = MenuItemCounter.objects.filter(cart = curr_cart).filter(item = MenuItem.objects.filter(id = item_id).first()).filter(custom_instructions = None)

        else:
            item_counters = MenuItemCounter.objects.filter(cart = curr_cart).filter(item = MenuItem.objects.filter(id = item_id).first()).filter(custom_instructions = request.POST['custom_instructions'])

        #check if the item is in the cart or not
        if len(item_counters) == 0:
            form = CustomOrderForm(request.POST)
            order = form.save(commit = False)
            order.cart = curr_cart
            order.item = curr_item
            #handle tip
            if curr_cart.tip != 0:
                if curr_cart.custom_tip:
                    order.price = order.quantity*order.item.price
                    order.save()
                    curr_cart.total += order.price
                    curr_cart.total_with_tip += order.price
                    curr_cart.save()
                else:
                    tip_percent = round(curr_cart.tip / curr_cart.total, 2) #calculate tip percentage
                    order.price = order.quantity*order.item.price
                    order.save()
                    curr_cart.total += order.price
                    curr_cart.tip = round(curr_cart.total * tip_percent, 2)
                    curr_cart.total_with_tip = curr_cart.total + curr_cart.tip
                    curr_cart.save()

            else:
                order.price = order.quantity*order.item.price
                order.save()
                curr_cart.total += order.price
                curr_cart.save()
            return redirect('/customers/view_menu/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))

        #else same item already exists in cart
        else:
            item_counter = item_counters.first()

            #handle tip
            if curr_cart.tip != 0:
                if curr_cart.custom_tip:
                    old_total = curr_cart.total - item_counter.price
                    #change itemcounter
                    item_counter.quantity += int(request.POST['quantity'])
                    item_counter.price = item_counter.quantity*item_counter.item.price
                    item_counter.save()
                    #update cart total price
                    curr_cart.total = old_total + item_counter.price
                    curr_cart.total_with_tip = item_counter.price + curr_cart.tip
                    curr_cart.save()
                else:
                    tip_percent = round(curr_cart.tip / curr_cart.total, 2) #calculate tip percentage
                    #get the old total price of the cart - total price of item
                    old_total = curr_cart.total - item_counter.price
                    #change itemcounter
                    item_counter.quantity += int(request.POST['quantity'])
                    item_counter.price = item_counter.quantity*item_counter.item.price
                    item_counter.save()
                    #update cart total price
                    curr_cart.total = old_total + item_counter.price
                    curr_cart.tip = round(curr_cart.total * tip_percent, 2)
                    curr_cart.total_with_tip = curr_cart.total + curr_cart.tip
                    curr_cart.save()
            else:
                #get the old total price of the cart - total price of item
                old_total = curr_cart.total - item_counter.price
                #change itemcounter
                item_counter.quantity += int(request.POST['quantity'])
                item_counter.price = item_counter.quantity*item_counter.item.price
                item_counter.save()
                #update cart total price
                curr_cart.total = old_total + item_counter.price
                curr_cart.save()
        #redirect to menu
        return redirect('/customers/view_menu/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))
    #if method isn't a post, just redirect to menu
    else:
        #redirect to menu
        form = CustomOrderForm()
        # context = {'form': form}
        return render(request, 'customers/view_item.html', context)
        # return redirect('/customers/view_menu/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))

''' When plus icon is pressed on view_cart, ajax sends cart_id and MenuItem_id to this view. Then,
    MenuItemCounter.quantity is increased by 1. Depending on whether the cart has tip, it calculates
    new totals and sends JSON response back to client'''
def ajax_increase_quantity(request):
    cart_id = request.GET.get('cart_id', None)
    menu_item_name = request.GET.get('menu_item', None)
    print('cart_id:', cart_id)
    print('menu_item:', menu_item_name)
    item_counters = MenuItemCounter.objects.filter(cart = cart_id).all()
    curr_cart = Cart.objects.filter(id = cart_id).first()

    for item_counter in item_counters:
        if item_counter.item.name == menu_item_name:
            old_total = curr_cart.total - item_counter.price
            item_counter.quantity += 1
            item_counter.price = round(item_counter.quantity * item_counter.item.price, 2)
            item_counter.save()
            quantity = item_counter.quantity
            price = item_counter.price
            #take into account tip
            if curr_cart.tip != 0:
                if curr_cart.custom_tip:
                    curr_cart.total = old_total + item_counter.price
                    curr_cart.total_with_tip += item_counter.item.price
                    curr_cart.save()
                    cart_total = curr_cart.total
                    cart_tip = curr_cart.tip
                    cart_total_with_tip = curr_cart.total_with_tip
                else:
                    tip_percent = round(curr_cart.tip / curr_cart.total, 2)
                    curr_cart.total = old_total + item_counter.price
                    curr_cart.tip = round(curr_cart.total * tip_percent, 2)
                    curr_cart.total_with_tip = curr_cart.total + curr_cart.tip
                    curr_cart.save()
                    cart_total = curr_cart.total
                    cart_tip = curr_cart.tip
                    cart_total_with_tip = curr_cart.total_with_tip
            #no tip included so far
            else:
                curr_cart.total = old_total + item_counter.price
                curr_cart.save()
                cart_total = curr_cart.total
                cart_tip = 0
                cart_total_with_tip = 0

    data = {
        'quantity': quantity,
        'price': price,
        'cart_total': cart_total,
        'cart_tip': cart_tip,
        'cart_total_with_tip': cart_total_with_tip
    }
    return JsonResponse(data)

def ajax_decrease_quantity(request):
    cart_id = request.GET.get('cart_id', None)
    menu_item_name = request.GET.get('menu_item', None)
    print('cart_id:', cart_id)
    print('menu_item:', menu_item_name)
    item_counters = MenuItemCounter.objects.filter(cart = cart_id).all()
    curr_cart = Cart.objects.filter(id = cart_id).first()

    for item_counter in item_counters:
        if item_counter.item.name == menu_item_name:
            old_total = curr_cart.total - item_counter.price
            item_counter.quantity -= 1
            item_counter.price = round(item_counter.quantity * item_counter.item.price, 2)
            item_counter.save()
            quantity = item_counter.quantity
            price = item_counter.price
            #take tip into account
            if curr_cart.tip != 0:
                if curr_cart.custom_tip:
                    curr_cart.total = old_total + item_counter.price
                    curr_cart.total_with_tip -= item_counter.item.price
                    curr_cart.save()
                    cart_total = curr_cart.total
                    cart_tip = curr_cart.tip
                    cart_total_with_tip = curr_cart.total_with_tip
                else:
                    tip_percent = round(curr_cart.tip / curr_cart.total, 2)
                    curr_cart.total = old_total + item_counter.price
                    curr_cart.tip = round(curr_cart.total * tip_percent, 2)
                    curr_cart.total_with_tip = curr_cart.total + curr_cart.tip
                    curr_cart.save()
                    cart_total = curr_cart.total
                    cart_tip = curr_cart.tip
                    cart_total_with_tip = curr_cart.total_with_tip
            #no tip included so far
            else:
                curr_cart.total = old_total + item_counter.price
                curr_cart.save()
                cart_total = curr_cart.total
                cart_tip = 0
                cart_total_with_tip = 0

    data = {
        'quantity': quantity,
        'price': price,
        'cart_total': cart_total,
        'cart_tip': cart_tip,
        'cart_total_with_tip': cart_total_with_tip
    }
    return JsonResponse(data)

"""this method gets a menuitemcounter, and changes the instructions, it NEEDS A NEW SET OF INSTRUCTIONS FROM A POST REQUEST AND A MENUITEMCOUNTER ID"""
def change_instructions(request, cart_id, restaurant_id, menu_id):
    if request.method == 'POST':
        item_counter = MenuItemCounter.objects.filter(id = request.POST['item_counter_id'])
        item_counter.instructions = request.POST['custom_instructions']
        item_counter.save()
        return redirect('/customers/view_cart/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))
    else:
        return redirect('/customers/view_cart/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))


"""this method gets called when item_quantity == 0. It totally removes item from cart, and changes the price of the cart accordingly"""
def remove_item(request, cart_id, restaurant_id, menu_id, item_id):
    if request.method == 'POST':
        curr_cart = Cart.objects.filter(id = cart_id).first()
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        items = MenuItemCounter.objects.filter(cart = curr_cart).all()
        item_remove = MenuItemCounter.objects.filter(cart = curr_cart).filter(id = item_id).first()
        remove_price = item_remove.price

        if curr_cart.tip != 0:
            if curr_cart.custom_tip:
                curr_cart.total -= remove_price
                curr_cart.total_with_tip -= remove_price
                item_remove.delete()
            else:
                tip_percent = round(curr_cart.tip / curr_cart.total, 2) #calculate tip percentage
                curr_cart.total -= remove_price
                curr_cart.tip = round(curr_cart.total * tip_percent, 2)
                curr_cart.total_with_tip = curr_cart.total + curr_cart.tip
                item_remove.delete()
        else:
            curr_cart.total -= remove_price
            item_remove.delete()

        curr_cart.save()

        return redirect('/customers/view_cart/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))
    else:
        curr_cart = Cart.objects.filter(id = cart_id).first()
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        items = MenuItemCounter.objects.filter(cart = curr_cart).all()
        return render(request, 'customers/view_cart.html', {'cart': curr_cart, 'items': items, 'restaurant': curr_rest, 'menu': curr_menu})

#this method displays the overview of a customers cart
def view_cart(request, cart_id, restaurant_id, menu_id):
    if request.method == 'GET':
        curr_cart = Cart.objects.filter(id = cart_id).first()
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        items = MenuItemCounter.objects.filter(cart = curr_cart).all()

        return render(request, 'customers/view_cart.html', {'cart': curr_cart, 'items': items, 'restaurant': curr_rest, 'menu': curr_menu})
    else:
        #if method is post, just redirect back to page
        return redirect('/customers/view_cart/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))

"""Calculates tip depending on what button is pressed. If custom tip, it is passed with POST method in form"""
def calculate_tip(request, cart_id, restaurant_id, menu_id, tip):
    if request.method == 'POST':
        curr_cart = Cart.objects.filter(id = cart_id).first()
        form = CustomTipForm(request.POST)

        if form.is_valid():
            curr_cart.custom_tip = True
            custom_tip = form.cleaned_data['tip']
            print("custom_tip", custom_tip)
            curr_cart.tip = custom_tip
            curr_cart.total_with_tip = curr_cart.total + custom_tip
            curr_cart.save()
        return redirect('/customers/view_cart/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))
    else:
        curr_cart = Cart.objects.filter(id = cart_id).first()
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        items = MenuItemCounter.objects.filter(cart = curr_cart).all()
        tip_amount = round(curr_cart.total * Decimal((tip / 100)), 2)
        curr_cart.custom_tip = False
        curr_cart.tip = tip_amount
        curr_cart.total_with_tip = curr_cart.total + tip_amount
        curr_cart.save()
        return render(request, 'customers/view_cart.html', {'cart': curr_cart, 'items': items, 'restaurant': curr_rest, 'menu': curr_menu})

""" This method creates a PaymentIntent (Stripe API), saves the paymentintent id to the cart model and renders
    payment.html. All Stripe stuff is handled in the JS scripts in the payment template. If the cart is
    already paid, it redirects to order_confirmation
"""
def payment(request, cart_id, restaurant_id, menu_id):
    #1st check if this bill has already been paid, someone could accidentally come here and pay something that they're not meant to
    cart = Cart.objects.filter(id = cart_id).first()
    if cart.is_paid == True:
        ''' If payed, just redirect to order confirmation'''
        return redirect('/customers/order_confirmation/{c_id}'.format(c_id = cart_id))
    #this needs to be a post!!! cannot risk someone accidentally getting here from a get request
    if request.method == 'POST':
        """
        It never makes it here, after the stripe form gets submitted, the redirect has to happen in Javascript
        The following commented out code will be handled in order_confirmation
        """
        # cart = Cart.objects.filter(id = cart_id).first()
        # cart.is_paid = True
        # cart.save()
        #print cart items to kitchen printer
        return redirect('/customers/order_confirmation/{c_id}'.format(c_id = cart_id))
    else:
        cart = Cart.objects.filter(id = cart_id).first()
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        if cart.total_with_tip == 0:
            cart.total_with_tip = cart.total
            cart.save()
        #stripe API stuff here
        stripe.api_key = settings.STRIPE_SECRET_KEY
        intent = stripe.PaymentIntent.create(
          amount=int((cart.total_with_tip*100)),
          currency='mxn',
           # Verify your integration in this guide by including this parameter
          metadata={'integration_check': 'accept_a_payment'},
        )
        cart.stripe_order_id = intent.id
        cart.save()
        #if method is a get, then they're inputting payment info
        return render(request, 'customers/payment.html', {'client_secret':intent.client_secret, 'cart': cart, 'restaurant': curr_rest, 'menu': curr_menu})


''' This is an intermediary step between payment and order confirmation. Email and Phone form'''
def card_email_receipt(request, cart_id, restaurant_id, menu_id):
    form = EmailForm()
    if request.method == 'GET':
        curr_cart = Cart.objects.filter(id = cart_id).first()
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        #create new order tracker if one DNE
        if OrderTracker.objects.filter(cart = curr_cart).exists() == False:
            tracker = OrderTracker(restaurant = curr_cart.restaurant, cart = curr_cart, is_complete = False, phone_number = None)
            tracker.save()
        return render(request, 'customers/card_email_receipt.html', {'cart': curr_cart, 'restaurant': curr_rest, 'menu': curr_menu, 'form': form})
    else:
        curr_cart = Cart.objects.filter(id = cart_id).first()
        form = EmailForm(request.POST)
        if form.is_valid():
            curr_user_email = form.cleaned_data['email_input']
            curr_cart.email = curr_user_email
            curr_cart.save()
            print('user_email:', curr_cart.email)
        if request.POST['phone_input'] != "":
            tracker = OrderTracker.objects.filter(cart = curr_cart).first()
            tracker.phone_number = request.POST['phone_input']
            tracker.save()
        return redirect('/customers/order_confirmation/{c_id}'.format(c_id = cart_id))

def cash_email_receipt(request, cart_id, restaurant_id, menu_id):
    '''Notify cashier that customer is paying cash'''
    form = EmailForm()
    if request.method == 'GET':
        curr_cart = Cart.objects.filter(id = cart_id).first()
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()
        #create new order tracker if one DNE
        if OrderTracker.objects.filter(cart = curr_cart).exists() == False:
            tracker = OrderTracker(restaurant = curr_cart.restaurant, cart = curr_cart, is_complete = False, phone_number = None)
            tracker.save()
        return render(request, 'customers/cash_email_receipt.html', {'cart': curr_cart, 'restaurant': curr_rest, 'menu': curr_menu, 'form': form})
    else:
        curr_cart = Cart.objects.filter(id = cart_id).first()
        form = EmailForm(request.POST)
        if form.is_valid():
            curr_user_email = form.cleaned_data['email_input']
            curr_cart.email = curr_user_email
            curr_cart.save()
            print('user_email:', curr_cart.email)
        if request.POST['phone_input'] != "":
            tracker = OrderTracker.objects.filter(cart = curr_cart).first()
            tracker.phone_number = request.POST['phone_input']
            tracker.save()
        return redirect('/customers/cash_code/{c_id}/{r_id}/{m_id}'.format(c_id = cart_id, r_id = restaurant_id, m_id = menu_id))

''' This view handles showing their cash code to the user if paying cash'''
def cash_payment_code(request, cart_id, restaurant_id, menu_id):
    if request.method == 'GET':
        curr_cart = Cart.objects.filter(id = cart_id).first()
        curr_rest = Restaurant.objects.filter(id = restaurant_id).first()
        curr_menu = Menu.objects.filter(id = menu_id).first()

        return render(request, 'customers/cash_code.html', {'cart': curr_cart, 'restaurant': curr_rest, 'menu': curr_menu})

def ajax_confirm_cash_payment(request):
    cart_id = request.GET.get('cart_id', None)
    curr_cart = Cart.objects.filter(id = cart_id).first()
    is_paid = curr_cart.is_paid

    data = {
        'is_paid': is_paid
    }

    return JsonResponse(data)

'''This method sends order to kitchen, changes cart.is_paid to true and renders the confirmation page'''
def order_confirmation(request, cart_id):
    #if this method is a get, then theyre seeing the confirmation page
    '''Send order to kitchen to print'''
    if request.method == 'GET':
        cart = Cart.objects.filter(id = cart_id).first()
        cart.is_paid = True
        cart.save()
        items = MenuItemCounter.objects.filter(cart = cart_id)
        return render(request, 'customers/order_confirmation.html', {'cart': cart, 'items': items})
    else:
        #if this is a post, just send back to the view cart page
        return redirect('/customers/view_cart/{c_id}'.format(c_id = cart_id))

'''Handles Feedback form in order_confirmation. '''
def feedback(request, cart_id):
    form = FeedbackForm()
    if request.method == 'POST':
        #handle feedback form
        cart = Cart.objects.filter(id = cart_id).first()
        form = FeedbackForm(request.POST)
        feedback = form.save(commit = False)
        feedback.cart = cart
        feedback.save()
        print(feedback.feedback)
        print(feedback.cart)
        messages.info(request, "Thank you for your feedback!")
        return redirect('/customers/order_confirmation/{c_id}'.format(c_id = cart_id))
    else:
        cart = Cart.objects.filter(id = cart_id).first()
        return render(request, 'customers/order_confirmation.html', {'cart': cart, 'form': form})

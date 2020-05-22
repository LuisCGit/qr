from django.urls import path
from . import views

urlpatterns = [
    path('<int:restaurant_id>/<int:menu_id>', views.create_cart),
    path('view_menu/<int:cart_id>/<int:restaurant_id>/<int:menu_id>', views.view_menu),
    path('view_item/<int:cart_id>/<int:restaurant_id>/<int:menu_id>/<int:item_id>', views.view_item),
    path('add_item/<int:cart_id>/<int:restaurant_id>/<int:menu_id>/<int:item_id>', views.add_item), #for adding item to cart
    path('remove_item/<int:cart_id>/<int:restaurant_id>/<int:menu_id>/<int:item_id>', views.remove_item), #for removing item from cart
    path('view_cart/<int:cart_id>', views.view_cart),
    path('payment/<int:cart_id>', views.payment),
    path('order_confirmation/<int:cart_id>', views.order_confirmation),
]

from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .signals import order_created
from .import models

user = get_user_model()

class ProductImageSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        product_id = self.context.get('product_id')
        return models.ProductImage.objects.create(product_id=product_id, **validated_data)

    class Meta:
        model = models.ProductImage
        fields = ['id', 'image']
        

class ProductSerializer(serializers.ModelSerializer):
    price_with_tax = serializers.SerializerMethodField(read_only=True)
    images = ProductImageSerializer(many=True)

    def get_price_with_tax(self, product):
        return product.unit_price * Decimal(1.1)

    def create(self, validated_data):
        product = models.Product.objects.create(**validated_data)
        product.save()
        return product

    def update(self, instance: models.Product, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.unit_price = validated_data.get('unit_price', instance.unit_price)
        instance.slug = validated_data.get('slug', instance.slug)
        instance.collection = validated_data.get('collection', instance.collection)
        instance.save()
        return instance

    class Meta:
        model = models.Product
        fields = ['id', 'title', 'description', 'inventory', 'unit_price',
                  'price_with_tax', 'slug', 'collection', 'images']


class CollectionSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        collection = models.Collection.objects.create(**validated_data)
        collection.save()
        return collection

    def update(self, instance: models.Collection, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.save()
        return instance

    class Meta:
        model = models.Collection
        fields = ['id', 'title', 'products_count']


class ReviewSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        product_id = self.context['product_id']
        review = models.Review.objects.create(product_id=product_id, **validated_data)
        review.save()
        return review

    def update(self, instance: models.Review, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.date = validated_data.get('date', instance.date)
        instance.product = self.context['product_id']
        instance.save()
        return instance

    class Meta:
        model = models.Review
        fields = ['name', 'description', 'date']


class SimpleProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Product
        fields = ['id', 'title', 'unit_price']


class CartItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    item_total_price = serializers.SerializerMethodField()

    def get_item_total_price(self, cart_item: models.CartItem):
        return cart_item.quantity * cart_item.product.unit_price

    class Meta:
        model = models.CartItem
        fields = ['id', 'product', 'quantity', 'item_total_price']


class AddCartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()

    def validated_product_id(self, value):
        if not models.Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError('No product with that product ID exists')
        return value

    def save(self, **kwargs):
        cart_id = self.context.get('cart_id')
        product_id = self.validated_data.get('product_id')
        quantity = self.validated_data.get('quantity')
        try:
            cart_item = models.CartItem.objects.get(cart_id=cart_id, product_id=product_id)
            cart_item.quantity += quantity
            cart_item.save()
            self.instance = cart_item
        except models.CartItem.DoesNotExist:
            cart_item = models.CartItem.objects.create(cart_id=cart_id, **self.validated_data)
            self.instance = cart_item
        return self.instance

    class Meta:
        model = models.CartItem
        fields = ['product_id', 'quantity']


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CartItem
        fields = ['quantity']


class CartSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    cart_total_price = serializers.SerializerMethodField()

    def get_cart_total_price(self, cart: models.Cart):
        price = 0
        for items in cart.items.all():
            price += items.quantity * items.product.unit_price
        return price

    class Meta:
        model = models.Cart
        fields = ['id', 'items', 'cart_total_price']


class CustomerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        if not user.objects.filter(pk=value).exists():
            raise serializers.ValidationError('No registration found for the user with this user id.')
        return value

    def save(self, **kwargs):
        user_id = self.validated_data.get('user_id')
        try:
            customer = models.Customer.objects.get(user_id=user_id)
            customer.save()
            self.instance = customer
        except models.Customer.DoesNotExist:
            customer = models.Customer.objects.create(**self.validated_data)
            self.instance = customer
        return self.instance

    class Meta:
        model = models.Customer
        fields = ['id', 'user_id', 'phone', 'birth_date', 'membership']


class SimpleCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Customer
        fields = ['id', 'phone', 'birth_date', 'membership']


class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    class Meta:
        model = models.OrderItem
        fields = ['id', 'quantity', 'product']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    class Meta:
        model = models.Order
        fields = ['id', 'customer_id', 'placed_at', 'payment_status', 'items']


class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()

    def validate_cart_id(self, cart_id):
        if not models.Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError('No cart with that ID exists')
        if models.CartItem.objects.filter(cart_id=cart_id).count() == 0:
            raise serializers.ValidationError('Cart is empty')
        return cart_id

    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data.get('cart_id')
            customer = models.Customer.objects.get(user_id=self.context.get('user_id'))
            order = models.Order.objects.create(customer=customer)
            cart_items = models.CartItem.objects \
                                .select_related('product') \
                                .filter(cart_id=cart_id)
            order_items = [
                models.OrderItem(
                    order = order,
                    product = item.product,
                    quantity = item.quantity
                )
                for item in cart_items
            ]
            models.OrderItem.objects.bulk_create(order_items)
            models.Cart.objects.filter(pk=cart_id).delete()
            order_created.send_robust(self.__class__, order=order)
            return order


class UpdateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Order
        fields = ['payment_status']
from django.shortcuts import get_object_or_404, redirect
from django.db.models.aggregates import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import status
from rest_framework.response import Response
from rest_framework import mixins
from rest_framework import viewsets
from .permissions import IsAdminOrReadOnly
from .pagination import DefaultPagination
from .filters import ProductFilter
from . import serializers
from . import models


class ProductViewSet(viewsets.ModelViewSet):
    queryset = models.Product.objects.prefetch_related('images').all()
    serializer_class = serializers.ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['title', 'description']
    ordering_fields = ['unit_price', 'last_update']
    pagination_class = DefaultPagination
    permission_classes = [IsAdminOrReadOnly]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return redirect('product-list')

    def destroy(self, request, *args, **kwargs):
        product = get_object_or_404(models.Product, pk=kwargs['pk'])
        if product.orderitem_set.count() > 0:
            return Response({'error': 'product cannot be deleted, associated with orderitem'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ProductImageViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ProductImageSerializer

    def get_serializer_context(self):
        return {'product_id': self.kwargs.get('product_pk')}

    def get_queryset(self):
        return models.ProductImage.objects.filter(product_id=self.kwargs.get('product_pk'))


class CollectionViewset(viewsets.ModelViewSet):
    queryset = models.Collection.objects.annotate(products_count=Count('product')).all()
    serializer_class = serializers.CollectionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        collection = get_object_or_404(models.Collection, pk=kwargs['pk'])
        if collection.featured_product is not None:
            return Response({'error': 'collection could not be deleted, featuring a product'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = models.Review.objects.all()
    serializer_class = serializers.ReviewSerializer

    def get_serializer_context(self):
        return {'product_id': self.kwargs['product_pk']}

    def get_queryset(self):
        return models.Review.objects.filter(product_id=self.kwargs['product_pk'])

class CartViewSet(mixins.RetrieveModelMixin,
                  mixins.CreateModelMixin,
                  mixins.DestroyModelMixin,
                  viewsets.GenericViewSet):

    serializer_class = serializers.CartSerializer

    def get_queryset(self):
        return models.Cart.objects.prefetch_related('items__product').all()


class CartItemViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'put', 'delete']

    def get_queryset(self):
        return models.CartItem.objects \
            .filter(cart_id=self.kwargs['cart_pk']) \
            .select_related('product')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return serializers.AddCartItemSerializer
        elif self.request.method == 'PUT':
            return serializers.UpdateCartItemSerializer
        return serializers.CartItemSerializer

    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = models.Customer.objects.all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'me':
            return serializers.SimpleCustomerSerializer
        return serializers.CustomerSerializer

    @action(detail=False, methods=['GET', 'PUT'], permission_classes=[IsAuthenticated])
    def me(self, request):
        customer = models.Customer.objects.get(user_id=request.user.id)
        if request.method == 'GET':
            serializer = serializers.SimpleCustomerSerializer(customer)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = serializers.SimpleCustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    
    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = serializers.CreateOrderSerializer(data=request.data, 
            context={'user_id': self.request.user.id})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        serializer = serializers.OrderSerializer(order)
        return Response(serializer.data)

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method == 'POST':
            return serializers.CreateOrderSerializer
        if self.request.method == 'PATCH':
            return serializers.UpdateOrderSerializer
        return serializers.OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return models.Order.objects.all()
        customer = models.Customer.objects.get(user_id=user.id)
        return models.Order.objects.filter(customer_id=customer.id)
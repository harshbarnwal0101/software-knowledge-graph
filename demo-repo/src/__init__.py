"""
Demo Repository — E-commerce sample project.
Used to test the Software Knowledge Graph ingestion pipeline.
"""
from demo_repo.src.services.user_service import UserService
from demo_repo.src.services.product_service import ProductService
from demo_repo.src.services.order_service import OrderService

__all__ = ["UserService", "ProductService", "OrderService"]

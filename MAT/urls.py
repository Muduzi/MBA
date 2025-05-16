"""
URL configuration for MAT project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

# for image uploading
from django.conf import settings
from django.conf.urls.static import static

from home.views import *
from User.views import (login_view, sign_up, logout_view, management, profile_form, department_view,
                        departments_view, employee_form)
from User.business import business, business_profile, edit_business_profile, taxes
from expenses.views import expenses_view
from expenses.expenses_dash import expenses_dash
from expenses.bufferexpense import buffer_expense_view, edit_buffer_expense
from expenses.setSupplier import set_supplier
from expenses.Accounts import expense_accounts, expense_account
from credits.views import credit_view, credit_form, credit_installment
from income.views import product_income
from debts.views import debt, debt_form, debt_installment
from income.product_income import product_sale, edit_product_sale
from income.service_income import (services, service_income, service_sale, service, package, service_category,
                                   edit_service_sale)
from income.setCustomer import set_customer
from income.invoice import invoice_form, invoices_view, generate_invoice_pdf, delivery_note, invoice_view
from income.service_income_dash import service_income_dash
from income.product_income_dash import product_income_dash
from inventory.views import inventory_view, add_inventory
from inventory.replenish import replenish
from statements.views1 import profit_and_loss_dash, balance_sheet
from statements.views import profit_and_loss_dash_range
from statements.doubleEntries import double_entry
from assets.views import assets_view, asset_form
from catalogue.views import (catalogue_view, market_view, category, add_category, add_product, edit_product,
                             view_product, view_buss_type_products)
from management.views import *
from statements.ProfitAndLoss import profit_and_loss

urlpatterns = [
    # login&logout
    path("login/", login_view, name="login"),
    path("sign_up/", sign_up, name="signUp"),
    path("logout/", logout_view, name="logout"),
    path("admin/", admin.site.urls),
    path("", home_view, name="home"),
    path("management/", management, name="manager"),
    path("Error/<str:code>/", display_error, name="errorMessage"),

    # user urls
    # user profile
    path("profile_form/", profile_form, name="signup"),

    # business
    path("business/", business, name="business"),
    path("business_profile/", business_profile, name="business_Profile"),
    path("business_profile/<int:id>/", business_profile, name="business_profile"),
    path("edit_business_profile/", edit_business_profile, name="edit_business_profile"),
    path("taxes/", taxes, name="taxes"),

    # department & staff
    path("departments/", departments_view, name="department"),
    path("department/<int:id>/", department_view, name="department"),
    path("employee_form/<str:purpose>/<int:id>/<int:ID>/", employee_form, name="employeeForm"),
    path("employee_form/", employee_form, name="employeeForm"),

    # expense urls
    path("expenses/", expenses_view, name="expenses"),
    path("expenses_dash/", expenses_dash, name="expensesDash"),
    path("buffer_expense/", buffer_expense_view, name='bufferExp'),
    path("buffer_expense/<int:id>/", buffer_expense_view, name='bufferExp'),
    path("edit_buffer_expense/<int:id>/", edit_buffer_expense, name='bufferExp'),
    path("expense_accounts/", expense_accounts, name='expenseAccounts'),
    path("expense_account/<int:id>/", expense_account, name='expenseAccount'),
    path("set_supplier/", set_supplier, name="assetsVendor"),
    path("set_supplier/<int:id>/", set_supplier, name="assetsVendor"),

    # credits
    path("credit/", credit_view, name="credit"),
    path("credit_installment/<int:id>/", credit_installment, name="creditInstallment"),
    path("credit_form/<int:id>/", credit_form, name="creditForm"),

    # product sales income urls
    path("product_income/", product_income, name="productIncome"),
    path('product_dash/', product_income_dash, name="serviceIncomeDash"),
    path("product_sale/", product_sale, name='productSale'),
    path("edit_product_sale/<int:id>/", edit_product_sale, name='editProductSale'),
    path("invoice_form/", invoice_form, name="invoiceForm"),
    path("invoice_form/<int:id>/<str:choice>/", invoice_form, name="invoiceForm"),
    path("invoice_form/<int:id>/", invoice_form, name="invoiceForm"),
    path("invoice_pdf/", generate_invoice_pdf, name="invoice"),
    path("invoice_pdf/<int:id>/", generate_invoice_pdf, name="invoice"),
    path("invoices/", invoices_view, name="invoices"),
    path("invoice/", invoice_view, name="invoice"),
    path("invoice/<int:id>/", invoice_view, name="invoice"),
    path("delivery_note/", delivery_note, name="deliveryNote"),
    # path('test/', test, name='test'),

    # service sales income
    path('service_income/', service_income, name="serviceIncome"),
    path('service_dash/', service_income_dash, name="serviceIncomeDash"),
    path('service/<int:id>/', service, name="registerService"),
    path('package/<int:id>/', package, name="package"),
    path('set_customer/<int:id>/',  set_customer, name="serviceSale"),
    path('set_customer/',  set_customer, name="serviceSale"),
    path('service_sale/', service_sale, name="serviceBuffer"),
    path('services/', services, name="services"),
    path('service_category/<int:id>/', service_category, name="serviceCategory"),
    path('edit_service_sale/<int:id>/', edit_service_sale, name="editServiceBuffer"),

    # debts
    path("debt/", debt, name="debt"),
    path("debt_installment/<int:id>/", debt_installment, name="debtInstallment"),
    path("debt_form/<int:id>/", debt_form, name="debtForm"),

    # inventory
    path("inventory/", inventory_view, name="inventory"),
    path("add_inventory/", add_inventory, name="inventory"),
    path("add_inventory/<int:id>/", add_inventory, name="inventory"),
    path("replenish/<int:id>/", replenish, name="replenish"),

    # statements
    path("profit_and_loss_dash_range/", profit_and_loss_dash_range, name="statement"),
    path("profit_and_loss_dash/", profit_and_loss_dash, name="statement1"),
    path("balance_sheet/", balance_sheet, name="balanceSheet"),
    path("double_entry/", double_entry, name="double_Entry"),
    path("profit_and_loss/", profit_and_loss, name="profit_and_loss"),

    # Asset urls
    path("assets/", assets_view, name="assets"),
    path("asset_form/", asset_form, name="asset_form"),
    path("asset_form/<int:id>/", asset_form, name="asset_form"),

    # management
    path("manager/", manager, name="management"),
    path("subscriptions/", subscriptions, name="subscriptions"),
    path("subscriber/<int:id>/", subscriber, name="addSubscription"),
    path("subscription/<int:id>/", subscription, name="subscription"),
    path("subscriptionSettings/", subscription_settings, name="subscriptionSettings"),
    path("editPlan/<int:id>", edit_plan, name="editPlan"),
    path("transactionInformation/<str:trans_type>/<int:trans_id>/", transaction_info, name="transactionInformation"),

    # catalogue
    path("market/", market_view, name="market"),
    path("catalogue/", catalogue_view, name="catalogue"),
    path("catalogue/<str:store_name>/", catalogue_view, name="catalogue"),
    path("addCategory/", add_category, name="addCategory"),
    path("category/", category, name="category"),
    path("category/<int:id>/", category, name="catalogue"),
    path("addProduct/", add_product, name="addProduct"),
    path("editProduct/<int:id>/", edit_product, name="editProduct"),
    path("viewProduct/<int:id>/", view_product, name="view_product"),
    path("marketSection/<str:business_type>/", view_buss_type_products, name="viewBusinessTypeProducts")

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

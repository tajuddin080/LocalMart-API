import requests


def get_products_by_location(loc:str):
    location = loc.capitalize()
    response = requests.get(f"http://127.0.0.1:8000/product?Location={location}")
    return response.json()


def add_user(user_data):
   
    u_data = user_data
    response = requests.post("http://127.0.0.1:8000/adduser",json=u_data)
    return response.json


if __name__ == "__main__":

    print("Enter the User Deatils to add")
    u_id = input("Enter the userid")
    u_name = input("Enter the user name")
    u_email = input("Enter user email")
    u_pword = input("Enter the password")
    if u_id.startswith("A"):
        role = "Admin"
    else:
        role = "Customer"
    location = input("Enter the location")
    user_data = {
        "UID": u_id,
        "UEMAIL": u_email,
        "UPWORD": u_pword,
        "ROLE": role,
        "LOCATION": location
    }
    result = add_user(user_data)
    print(result)
    """location = input("Enter the location to see the products: ")
    products = get_products_by_location(location)
    for product in products:
        print("-"*25)
        for key,value in product.items():
            print(f"{key}:{value}")
        print("-"*25)"""

    

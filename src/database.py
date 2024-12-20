from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import uuid
from datetime import datetime
from datetime import date
import os
import certifi
from dotenv import load_dotenv

load_dotenv()

uri =os.getenv("MONGO_URI")
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["P2PLend"]
try:
    client.admin.command('ping')
except Exception as e:
    print(e)


def group_creation(name, admin_id, admin_password, join_code, admin_name, upi_id, repay_time):
    
    record = {"name": name, "admin_id": admin_id, "admin_password": admin_password, "join_code": join_code, "upi_id": upi_id, "repay_time": repay_time}
    collection = db["Groups"]
    
    collection.insert_one(record)
    add_member(name, admin_id, admin_name)
    return True


def add_transaction(borrower_id, lender_id, group_id, loan_amount, interest, return_time):
    transaction = db["Transaction"]
    
    current_date = datetime.now()

    record = {
        "Borrower_id": borrower_id,
        "Lender_id": lender_id,
        "Group_id": group_id,
        "loan_amount": loan_amount,
        "return_time": return_time,
        "interest": interest,
        "Return_status": "Pending",
        "transaction_date": current_date  # Add current date to the record
    }
    
    transaction.insert_one(record)

def admin_login(admin_id, admin_password, group_name):
    group = db["Groups"]
    if not (group.find_one({"admin_id": admin_id, "admin_password": admin_password, "name": group_name})):
        return False
    return True
    
def remove_member(member_name, group_name):
    collection = db["Members"]
    group_id = db["Groups"].find_one({"name": group_name}).get("_id")
    result = collection.delete_one({"Member_name": member_name, "Group_id": group_id})
    if result.deleted_count == 1:
        return "Member removed successfully."
    else:
        return "Entry not found." 
    

def leave_group(member_name,member_id,group_name):
    member_collection=db["Members"]
    group_id=db["Groups"].find_one({"name":group_name}).get("_id")
    existing_member = member_collection.find_one({"telegram_id": member_id})
    if existing_member:
        group_ids= existing_member.get("Group_id",[])
        if group_id not in group_ids:
            return False
        else:
            member_collection.update_one({"telegram_id":member_id},{"$pull":{"Group_id":group_id}})
            return True
    else:
        return False


def add_member(group_name, member_id, member_name, upi_id=None, phone_number=None):
    member_collections = db["Members"]
    group_id = db["Groups"].find_one({"name": group_name}).get("_id")
    existing_member = member_collections.find_one({"telegram_id": member_id})
    if existing_member:
        group_ids = existing_member.get("Group_id", [])
        if not isinstance(group_ids, list):
            group_ids = [group_ids]
        if group_id not in group_ids:
            group_ids.append(group_id)
            update_data = {"$set": {"Group_id": group_ids, "Member_name": member_name}}
            # Update UPI ID and phone number if provided
            if upi_id:
                update_data["$set"]["upi_id"] = upi_id
            if phone_number:
                update_data["$set"]["phone_number"] = phone_number
            member_collections.update_one({"telegram_id": member_id}, update_data)
            return True
        else:
            return False
    else:
        record = {"telegram_id": member_id, "Group_id": [group_id], "authentication details": 000, "points": 0, "Member_name": member_name}
        # Add UPI ID and phone number to the record if provided
        if upi_id:
            record["upi_id"] = upi_id
        if phone_number:
            record["phone_number"] = phone_number
        member_collections.insert_one(record)
        return True

def get_admin_id(group_name):
    group = db["Groups"]
    document = group.find_one({"name": group_name})
    if document:
        return document.get("admin_id")
    return None

def get_group_name(admin_id):
    group = db["Groups"]
    document = group.find_one({"admin_id": admin_id})
    if document:
        return document.get("name")
    return None

def get_upi_id(member_name):
    member_collection = db["Members"]
    document = member_collection.find_one({"Member_name": member_name})
    if document:
        return document.get("upi_id")
    return None


def is_join_code_correct(group_name, join_code):
    group = db["Groups"]
    document = group.find_one({"name": group_name, "join_code": join_code})
    return bool(document)

def is_group_exists(group_name):
    group = db["Groups"]
    document = group.find_one({"name": group_name})
    return bool(document)

def add_proposal(lender_id, group_id, interest, loan_amount, borrower_id,loan_uuid):
    try:
        collection = db["Proposals"]
        record = {
            "proposal_id": loan_uuid,
            "lender_id": lender_id,
            "borrower_id": borrower_id,
            "loan_amount": loan_amount,
            "group_id": group_id,
            "interest": interest
        }
        collection.insert_one(record)
        return "Your proposal added successfully."
    except Exception as e:
        return f"Error occurred while adding proposal: {str(e)}"


def show_proposals(loan_uuid):
    try:
        collection = db["Proposals"]
        proposals = list(collection.find({"proposal_id": loan_uuid}))  
        count = len(proposals)
        if count == 0:
            return "No proposals found."
        else:
            return proposals  
    except Exception as e:
        return f"Error occurred while fetching proposals: {str(e)}"


def lend_proposals(lender_tid, group_name, interest, borrower_tid=None):
    collection = db["Active_Proposals"]
    group_id = db["Groups"].find_one({"name": group_name}).get("_id")
    record = {"group_id": group_id, "lender_id": lender_tid, "borrower_id": borrower_tid, "interest": interest}
    collection.insert_one(record)
    return "Offer made successfully"


def display_proposals(member_id,group_name):
    collection = db["Active_Proposals"]
    group_id = db["Groups"].find_one({"name": group_name}).get("_id")
    proposals = collection.find({"borrower_id": member_id, "group_id": group_id}, {"_id": 1, "interest": 1})
    return proposals

def delete_group(group_name, admin_password):
    group_collection = db["Groups"]
    group_id = db["Groups"].find_one({"name": group_name}).get("_id")
    admin_id = get_admin_id(group_name)
    
    if not admin_login(admin_id, admin_password, group_name):
        return "Incorrect admin password"
    
    result = group_collection.delete_one({"name": group_name})
    
    if result.deleted_count == 1:
        remove_group_id_from_members(group_id)
        return f"Group '{group_name}' deleted successfully."
    else:
        return f"Group '{group_name}' not found."

def remove_group_id_from_members(group_id):
    member_collection = db["Members"]
    member_collection.update_many({}, {"$pull": {"Group_id": group_id}})

def get_group_members(group_name):
    member_collection = db["Members"]
    group_id = db["Groups"].find_one({"name": group_name}).get("_id")
    members = member_collection.find({"Group_id": group_id}, {"Member_name": 1})
    return list(members)

def get_groups_of_member(member_id):
    member_collection = db["Members"]
    member_document = member_collection.find_one({"telegram_id": member_id}, {"Group_id": 1})
    if member_document:
        group_ids = member_document.get("Group_id", [])
        group_collection = db["Groups"]
        member_groups = group_collection.find({"_id": {"$in": group_ids}}, {"name": 1})
        return [group['name'] for group in member_groups]
    else:
        return []

def get_group_id(group_name):
    group_collection = db["Groups"]
    group_document = group_collection.find_one({"name": group_name}, {"_id": 1})
    if group_document:
        return group_document.get("_id")
    else:
        return None
    
#after payment
def amount_payable(p,i,t):
     total_amount = p + i*t
     return total_amount

def show_defaulter(group_name):
    group_id = get_group_id(group_name)
    transactions = db["Transaction"].find({"admin_id": group_id})
    member = db["Members"]
    today_date = date.today()
    pending = []
    for i in transactions:
        if(i["Return_status"]=='Pending'):
            time = ((today_date - i["transaction_date"]).date()).days 
            if(time >= i["return_time"]):
                borrower_name = member.find_one({"_id":i["Borrower_id"]}).get("Member_name"),
                lender_name = member.find_one({"_id":i["Lender_id"]}).get("Member_name")
                net_amount = amount_payable(i["loan_amount"],i["interest"], time)
                j = {"borrower_name": borrower_name, "lender_name": lender_name, "Net amount": net_amount, "Transaction date": i["Transaction_date"], "Return date": i["Transaction_date"]+timedelta(days=i["return_time"])}
                pending.append(j)
    return pending  


def display_pending_transactions(user_id):
    transactions = db["Transaction"].find({"Borrower_id": user_id, "Return_status": "Pending"})
    transaction_list = []
    for transaction in transactions:
        group = db["Groups"].find_one({"_id": transaction["Group_id"]}, {"name": 1})
        if group:
            group_name = group["name"]
        else:
            group_name = "Unknown"  # Handle case where group is not found
        transaction_dict = {
            "_id": transaction["_id"],  # Include the MongoDB _id field
            "Borrower_id": transaction["Borrower_id"],
            "Lender_id": transaction["Lender_id"],
            "Group_id": transaction["Group_id"],
            "loan_amount": transaction["loan_amount"],
            "return_time": transaction["return_time"],
            "interest": transaction["interest"],
            "Return_status": transaction["Return_status"],
            "transaction_date": transaction["transaction_date"],
            "Group_name": group_name
        }
        transaction_list.append(transaction_dict)
    return transaction_list


def member_exists(member_id):
    member_collection = db["Members"]
    member_document = member_collection.find_one({"telegram_id": member_id})
    return bool(member_document)

def get_group_name(group_id):
    group_collection = db["Groups"]
    group_document = group_collection.find_one({"_id": group_id}, {"name": 1})
    if group_document:
        return group_document.get("name")
    else:
        return None
    
def already_member_of_group(member_id, group_id):
    member_collection = db["Members"]
    member_document = member_collection.find_one({"telegram_id": member_id})
    if member_document:
        group_ids = member_document.get("Group_id", [])
        return group_id in group_ids
    else:
        return False

def add_old_member(member_id, group_id):
    member_collection = db["Members"]
    member_collection.update_one({"telegram_id": member_id}, {"$push": {"Group_id": group_id}})
    
def get_admin_upi_id(group_name):
    group = db["Groups"]
    document = group.find_one({"name": group_name})
    return document.get("upi_id")

def get_group_repay_time(group_id):
    group = db["Groups"]
    document = group.find_one({"_id": group_id}) 
    return document.get("repay_time")

def get_member_name(member_id):
    member_collection = db["Members"]
    document = member_collection.find_one({"telegram_id": member_id})
    return document.get("Member_name")

def get_admin_groups(admin_id):
    group_collection = db["Groups"]
    group_documents = group_collection.find({"admin_id": admin_id}, {"name": 1})
    return [group['name'] for group in group_documents]


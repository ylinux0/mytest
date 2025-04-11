# hubspot.py

import datetime
import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import hashlib
import requests
from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# HubSpot OAuth configuration
CLIENT_ID = '9698d4c9-740c-42ea-b318-0192c159e12c'  # Replace with your HubSpot client ID
CLIENT_SECRET = '84fcb016-9b15-4ad2-a774-534b7659752a'  # Replace with your HubSpot client secret
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
SCOPES = 'oauth'  # Basic oauth scope
AUTHORIZATION_URL = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&scope={SCOPES}&redirect_uri={REDIRECT_URI}'

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')
    
    auth_url = f'{AUTHORIZATION_URL}&state={encoded_state}'
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', json.dumps(state_data), expire=600)
    
    return auth_url

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description'))
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))
    
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')
    
    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    
    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.hubapi.com/oauth/v1/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': REDIRECT_URI,
                'code': code
            }
        )
    
    await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)
    
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
    return credentials

def create_integration_item_metadata_object(response_json, item_type, parent_id=None, parent_name=None):
    return IntegrationItem(
        id=f"{response_json.get('id', '')}_{item_type}",
        name=response_json.get('properties', {}).get('name', response_json.get('name', '')),
        type=item_type,
        parent_id=parent_id,
        parent_path_or_name=parent_name
    )

async def get_items_hubspot(credentials):
    credentials = json.loads(credentials)
    access_token = credentials.get('access_token')
    headers = {'Authorization': f'Bearer {access_token}'}
    
    list_of_integration_items = []
    
    # Fetch contacts
    contacts_url = 'https://api.hubapi.com/crm/v3/objects/contacts'
    contacts_response = requests.get(contacts_url, headers=headers)
    if contacts_response.status_code == 200:
        for contact in contacts_response.json().get('results', []):
            list_of_integration_items.append(
                create_integration_item_metadata_object(contact, 'Contact')
            )
    
    # Fetch companies
    companies_url = 'https://api.hubapi.com/crm/v3/objects/companies'
    companies_response = requests.get(companies_url, headers=headers)
    if companies_response.status_code == 200:
        for company in companies_response.json().get('results', []):
            list_of_integration_items.append(
                create_integration_item_metadata_object(company, 'Company')
            )
    
    # Fetch deals
    deals_url = 'https://api.hubapi.com/crm/v3/objects/deals'
    deals_response = requests.get(deals_url, headers=headers)
    if deals_response.status_code == 200:
        for deal in deals_response.json().get('results', []):
            list_of_integration_items.append(
                create_integration_item_metadata_object(deal, 'Deal')
            )
    
    return list_of_integration_items
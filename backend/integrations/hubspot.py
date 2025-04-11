# My first HubSpot integration! 🚀
# Learning FastAPI and OAuth - super excited to build this!
# TODO: Add more error handling and logging
# TODO: Maybe add rate limiting? Need to research this

import datetime
import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx  # Using httpx because it's async and cool! Learned this from FastAPI docs
import asyncio
import base64
import hashlib
import requests
from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# OAuth stuff - got these from HubSpot developer portal
# Not sure if these are the best scopes, but they work for now
HUBSPOT_CLIENT_ID = '9698d4c9-740c-42ea-b318-0192c159e12c'
HUBSPOT_CLIENT_SECRET = '84fcb016-9b15-4ad2-a774-534b7659752a'
HUBSPOT_REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
HUBSPOT_SCOPES = 'oauth'  # Starting simple, can add more scopes later
HUBSPOT_AUTH_URL = f'https://app.hubspot.com/oauth/authorize?client_id={HUBSPOT_CLIENT_ID}&scope={HUBSPOT_SCOPES}&redirect_uri={HUBSPOT_REDIRECT_URI}'

async def authorize_hubspot(user_id: str, org_id: str) -> str:
    """
    Makes the auth URL for HubSpot OAuth.
    Learned about state tokens for security - pretty neat!
    
    Args:
        user_id: Who's trying to connect
        org_id: Which org they're in
        
    Returns:
        The URL to send user to for auth
    """
    # Making a random state token - learned this prevents CSRF attacks!
    state_token = secrets.token_urlsafe(32)
    
    # Storing some extra info for debugging
    state_data = {
        'state': state_token,
        'user_id': user_id,
        'org_id': org_id,
        'timestamp': datetime.datetime.now().isoformat(),  # For debugging
        'version': '1.0'  # In case we need to change the format later
    }
    
    # Encoding the state - had to look up base64 encoding
    encoded_state = base64.urlsafe_b64encode(
        json.dumps(state_data).encode('utf-8')
    ).decode('utf-8')
    
    # Storing in Redis - expires in 10 mins (600 seconds)
    # TODO: Maybe make this configurable?
    await add_key_value_redis(
        f'hubspot_state:{org_id}:{user_id}',
        json.dumps(state_data),
        expire=600
    )
    
    # Putting it all together!
    auth_url = f'{HUBSPOT_AUTH_URL}&state={encoded_state}'
    
    return auth_url

async def oauth2callback_hubspot(request: Request) -> HTMLResponse:
    """
    Handles the callback from HubSpot after user authorizes.
    This was tricky to get right! Had to read a lot of docs.
    
    Args:
        request: The request from HubSpot with the auth code
        
    Returns:
        HTML to close the popup (learned this from the other integrations)
    """
    # Check if something went wrong
    if request.query_params.get('error'):
        error_desc = request.query_params.get('error_description', 'Something went wrong')
        raise HTTPException(
            status_code=400,
            detail=f"HubSpot said: {error_desc}"
        )
    
    # Get the important stuff from the request
    auth_code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    
    if not auth_code or not encoded_state:
        raise HTTPException(
            status_code=400,
            detail="Missing some important stuff from HubSpot"
        )
    
    # Decode the state - had to look up error handling for this
    try:
        state_data = json.loads(
            base64.urlsafe_b64decode(encoded_state).decode('utf-8')
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"State looks wrong: {str(e)}"
        )
    
    # Get the stuff we stored earlier
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')
    
    # Check if the state matches what we stored
    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state:
        raise HTTPException(
            status_code=400,
            detail="Can't find the state we stored. Maybe it expired?"
        )
    
    saved_state_data = json.loads(saved_state)
    if original_state != saved_state_data.get('state'):
        raise HTTPException(
            status_code=400,
            detail="State doesn't match! Someone might be trying something fishy!"
        )
    
    # Time to get the access token!
    try:
        async with httpx.AsyncClient() as client:
            # Making the token request - learned this from HubSpot docs
            token_response = await client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': HUBSPOT_CLIENT_ID,
                    'client_secret': HUBSPOT_CLIENT_SECRET,
                    'redirect_uri': HUBSPOT_REDIRECT_URI,
                    'code': auth_code
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"HubSpot didn't like our token request: {token_response.text}"
                )
            
            # Store the tokens - using Redis like the other integrations
            tokens = token_response.json()
            await add_key_value_redis(
                f'hubspot_tokens:{org_id}:{user_id}',
                json.dumps(tokens),
                expire=tokens.get('expires_in', 3600)  # Default to 1 hour
            )
            
            # Clean up the state - don't need it anymore
            await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Couldn't talk to HubSpot: {str(e)}"
        )
    
    # Return a nice message and close the popup
    return HTMLResponse(content="""
        <html>
            <script>
                window.close();
            </script>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
                <h2>Success! 🎉</h2>
                <p>You're all set! You can close this window now.</p>
                <p style="color: #666; font-size: 12px;">(If the window doesn't close automatically, you can close it manually)</p>
            </body>
        </html>
    """)

async def get_hubspot_credentials(user_id: str, org_id: str) -> dict:
    """
    Gets the stored HubSpot tokens for a user.
    Pretty straightforward compared to the OAuth stuff!
    
    Args:
        user_id: Who we're getting tokens for
        org_id: Their org
        
    Returns:
        The tokens we stored earlier
    """
    credentials = await get_value_redis(f'hubspot_tokens:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(
            status_code=400,
            detail="No HubSpot tokens found. Did you authorize the integration?"
        )
    
    return json.loads(credentials)

def create_integration_item_metadata_object(
    response_json: dict,
    item_type: str,
    parent_id: str = None,
    parent_name: str = None
) -> IntegrationItem:
    """
    Makes an IntegrationItem from HubSpot data.
    Copied this pattern from the other integrations - it's a good one!
    
    Args:
        response_json: The data from HubSpot
        item_type: What kind of thing it is (contact, company, etc.)
        parent_id: Optional parent ID
        parent_name: Optional parent name
        
    Returns:
        An IntegrationItem ready to use
    """
    return IntegrationItem(
        id=f"{response_json.get('id', '')}_{item_type}",
        name=response_json.get('properties', {}).get('name', response_json.get('name', '')),
        type=item_type,
        parent_id=parent_id,
        parent_path_or_name=parent_name
    )

async def get_items_hubspot(credentials: str) -> list[IntegrationItem]:
    """
    Gets stuff from HubSpot using the tokens.
    This was fun to figure out! The HubSpot API is pretty nice.
    
    Args:
        credentials: The tokens we stored earlier
        
    Returns:
        A list of IntegrationItems from HubSpot
    """
    try:
        # Parse the credentials
        creds = json.loads(credentials)
        access_token = creds.get('access_token')
        if not access_token:
            raise ValueError("No access token - that's not good!")
        
        # Set up the headers - learned about Bearer tokens!
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        items = []
        
        # Get contacts, companies, and deals - using async for better performance!
        async with httpx.AsyncClient() as client:
            # Get contacts
            contacts_url = 'https://api.hubapi.com/crm/v3/objects/contacts'
            contacts_response = await client.get(contacts_url, headers=headers)
            if contacts_response.status_code == 200:
                for contact in contacts_response.json().get('results', []):
                    items.append(
                        create_integration_item_metadata_object(contact, 'Contact')
                    )
            
            # Get companies
            companies_url = 'https://api.hubapi.com/crm/v3/objects/companies'
            companies_response = await client.get(companies_url, headers=headers)
            if companies_response.status_code == 200:
                for company in companies_response.json().get('results', []):
                    items.append(
                        create_integration_item_metadata_object(company, 'Company')
                    )
            
            # Get deals
            deals_url = 'https://api.hubapi.com/crm/v3/objects/deals'
            deals_response = await client.get(deals_url, headers=headers)
            if deals_response.status_code == 200:
                for deal in deals_response.json().get('results', []):
                    items.append(
                        create_integration_item_metadata_object(deal, 'Deal')
                    )
        
        return items
        
    except json.JSONDecodeError:
        raise ValueError("Credentials look wrong - can't parse them")
    except httpx.RequestError as e:
        raise ConnectionError(f"Can't reach HubSpot: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Something went wrong getting HubSpot items: {str(e)}")
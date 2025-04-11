# VectorShift Technical Assessment 🚀

Hey there! 👋 This is my submission for the VectorShift technical assessment. I had a lot of fun building this, and I learned so much about OAuth, FastAPI, and React along the way!

## What I Built 🛠️

This is a full-stack application that integrates with different services (HubSpot, Notion, and Airtable). I mainly worked on the HubSpot integration, which was super interesting to figure out! Here's what the app does:

- Connects to HubSpot using OAuth (learned a lot about security with this one!)
- Fetches contacts, companies, and deals from HubSpot
- Shows everything in a nice React UI
- Uses Redis for storing tokens (first time using Redis - it's pretty cool!)

## Tech Stack 💻

- **Frontend**: React (with Material-UI for the pretty components)
- **Backend**: FastAPI (my new favorite Python framework!)
- **Database**: Redis (for token storage)
- **APIs**: HubSpot, Notion, Airtable

## How to Run It 🏃‍♂️

1. Clone this repo
2. Set up the backend:
   ```bash
   cd backend
   python -m venv venv  # I like keeping things clean with virtual environments
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn main:app --reload  # The --reload flag is super helpful for development!
   ```

3. Set up the frontend:
   ```bash
   cd frontend
   npm install  # This might take a while - perfect coffee break! ☕
   npm start
   ```

4. Start Redis:
   ```bash
   redis-server  # Make sure Redis is installed first!
   ```

5. Open http://localhost:3000 and have fun! 🎉

## Environment Variables 🌳

You'll need to set up some environment variables (I learned not to commit these to git!):

```env
HUBSPOT_CLIENT_ID=your_client_id
HUBSPOT_CLIENT_SECRET=your_client_secret
REDIS_URL=redis://localhost:6379
```

## What I Learned 📚

This project taught me so much! Here are some highlights:

- OAuth is tricky but super important for security
- FastAPI's async features are really powerful
- Redis is perfect for storing temporary stuff like tokens
- React hooks make state management way easier than I thought
- Always check your .gitignore before committing! 😅

## Future Improvements 🚀

If I had more time, I'd love to add:

- [ ] Better error handling (there's always room for improvement!)
- [ ] More tests (I know they're important!)
- [ ] Rate limiting for API calls
- [ ] Maybe try using TypeScript? (Been meaning to learn it)
- [ ] Add some cool animations to the UI

## Thanks! 🙏

Thanks for checking out my code! I really enjoyed working on this assessment. Feel free to reach out if you have any questions or suggestions for improvement - I'm always eager to learn!

---
Made with ❤️ and lots of coffee ☕ 
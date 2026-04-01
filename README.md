# PrepAI Backend
This folder contains the FastAPI backend for PrepAI.

## Deployment on Render

This project is configured for easy deployment on Render using the included `render.yaml` file.

### Steps to Deploy:
1. Connect your GitHub repository to Render.
2. Render will automatically detect the `render.yaml` file and set up the service.
3. **Important**: You must manually set the following environment variables in the Render dashboard:
   - `MONGODB_URL`: Your MongoDB connection string.
   - `DATABASE_NAME`: The name of your database (e.g., `exam_aura`).
   - `GROQ_API_KEY`: Your Groq API key for AI explanations.
4. The `SECRET_KEY` will be automatically generated if not provided.

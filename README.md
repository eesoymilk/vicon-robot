# LLM User Modeling Wheelchair Robot

 This repository contains the code for the user modeling wheelchair robot project. The project aims to develop a wheelchair robotic arm that can understand the user's intent and navigate accordingly. The project uses large language models to understand the user's intent and navigate the wheelchair robot accordingly. This project consists of three applications, they communicate each other using Redis. The three applications are:

- **LLM Agent**: This application is responsible for understanding the user's intent. It uses OpenAI's function calling API to understand the user's intent and sends the intent as a command to the robot controller.

- **Robot Controller**: This application is responsible for controlling the robot. It receives the intent from the LLM Agent and navigates the robot accordingly.

- **Vicon Tracking**: This application is responsible for tracking positions of the objects in the environment. It sends the position of the objects to the LLM Agent.

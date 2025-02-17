import os
import gradio as gr
from sql_agent.agno_agent import Text2SQLAgent
from sql_agent.utils import logger 
from sql_agent.prompt import FULL_REPORT

log = logger.get_logger(__name__)
log = logger.init(level="DEBUG", save_log=True)

UI_PORT: int = int(os.getenv("UI_PORT", "8046"))
PLACE_HOLDER = "¡Hola! ¿En qué puedo ayudarte?"
BOTH_ICON = "app/assets/bot.png"
USER_ICON = "app/assets/user.png"



def respond(question, history):
    """ Respond to user input. """
    agent = Text2SQLAgent(db_url='sqlite:///app/data/shop.db')
    sql_query, answer =  agent.request(question)
    response  = FULL_REPORT.format(sql_query=sql_query, sql_results=answer)
    return response

chatbot = gr.ChatInterface(
    fn=respond,
    type="messages",
    chatbot=gr.Chatbot(elem_id="chatbot", height="auto", avatar_images=[USER_ICON, BOTH_ICON]),
    title="Text2SQLAgent with Agno",
    textbox=gr.Textbox(placeholder=PLACE_HOLDER, container=False, scale=7),
    submit_btn="Enviar",
    theme=gr.themes.Default(primary_hue="blue", secondary_hue="indigo"),
    examples=["¿Cuáles son los productos disponibles en la categoría 'Women'?","¿Qué productos han sido comprados en el pedido con ID 3?","¿Qué productos tienen un precio superior a 120?"],
)

if __name__ == "__main__":

    log.info("Starting chatbot...")
    chatbot.launch(server_port=UI_PORT)

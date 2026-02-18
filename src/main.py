import click
import multiprocessing
import time
from src.agents.coordinator import CoordinatorAgent
from src.agents.specialists import (
    create_grammar_agent, 
    create_clarity_agent, 
    create_tone_agent, 
    create_structure_agent
)
from src.agents.aggregator import AggregatorAgent
from src.ingestion.producer import produce_document as producer_cmd

@click.group()
def cli():
    pass

@cli.command()
def coordinator():
    """Run the Coordinator Agent"""
    agent = CoordinatorAgent()
    agent.run()

@cli.command()
@click.option("--type", required=True, type=click.Choice(["grammar", "clarity", "tone", "structure"]), help="Specialist type")
def specialist(type):
    """Run a Specialist Agent"""
    if type == "grammar":
        agent = create_grammar_agent()
    elif type == "clarity":
        agent = create_clarity_agent()
    elif type == "tone":
        agent = create_tone_agent()
    elif type == "structure":
        agent = create_structure_agent()
    
    agent.run()

@cli.command()
def aggregator():
    """Run the Aggregator Agent"""
    agent = AggregatorAgent()
    agent.run()

@cli.command()
@click.option("--doc_id", default="doc-demo-1")
@click.option("--paragraphs", default=3)
def produce(doc_id, paragraphs):
    """Produce a test document"""
    from src.ingestion.producer import run_producer
    run_producer(doc_id, paragraphs)

@cli.command()
def start_all():
    """Run all agents in parallel (demo mode)"""
    processes = []
    
    # 1 Coordinator
    # We instantiate inside the target function to avoid pickling open redis connections if any
    def run_coordinator():
        CoordinatorAgent().run()

    p_coord = multiprocessing.Process(target=run_coordinator)
    p_coord.start()
    processes.append(p_coord)
    
    # 4 Specialists
    def run_specialist(type_):
        if type_ == "grammar":
            create_grammar_agent().run()
        elif type_ == "clarity":
            create_clarity_agent().run()
        elif type_ == "tone":
            create_tone_agent().run()
        elif type_ == "structure":
            create_structure_agent().run()

    for type_ in ["grammar", "clarity", "tone", "structure"]:
        p = multiprocessing.Process(target=run_specialist, args=(type_,))
        p.start()
        processes.append(p)
        
    # 1 Aggregator
    def run_aggregator():
        AggregatorAgent().run()

    p_agg = multiprocessing.Process(target=run_aggregator)
    p_agg.start()
    processes.append(p_agg)
    
    print("All agents started. Press Ctrl+C to stop.")
    
    try:
        # Join processes
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("Stopping all agents...")
        for p in processes:
            p.terminate()

if __name__ == "__main__":
    cli()

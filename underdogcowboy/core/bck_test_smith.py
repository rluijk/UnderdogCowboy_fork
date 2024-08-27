# 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

import os
import time
from tracing import LangSmithTracer

    
def main():
    tracer = LangSmithTracer(api_key="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")
    
    # Include inputs when starting the trace
    with tracer.trace("Main Process", inputs={"param1": "value1", "param2": "value2"}):
        print("Starting main process")
        tracer.log("initial_status", "Process started")

        # Include inputs when starting the span
        with tracer.span("Data Processing", inputs={"data": [1, 2, 3]}):
            print("Processing data")
            time.sleep(1)
            tracer.log("processed_items", 100)

        # Include inputs when starting the span
        with tracer.span("Calculation", inputs={"initial_value": 21}):
            print("Performing calculations")
            time.sleep(0.5)
            result = 42
            tracer.log("calculation_result", result)

        tracer.log_metric("process_duration", 1.5)
        print("Main process completed")


    tracer.flush()

if __name__ == "__main__":
    main()
    print("Script execution completed")
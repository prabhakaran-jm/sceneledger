import { DEMO_STEPS, type DemoStepId } from "@/lib/demo";

type DemoStepperProps = {
  completion: Record<DemoStepId, boolean>;
};

export function DemoStepper({ completion }: DemoStepperProps) {
  return (
    <nav className="demo-stepper" aria-label="Demo progress">
      <ol className="demo-stepper-list">
        {DEMO_STEPS.map((step) => {
          const done = completion[step.id];
          return (
            <li
              key={step.id}
              className={`demo-step${done ? " demo-step-done" : ""}`}
            >
              <span className="demo-step-num">{step.id}</span>
              <span className="demo-step-label">{step.label}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

import { DEMO_STEPS, type DemoStepId } from "@/lib/demo";
import { Icon } from "./ui";

type DemoStepperProps = {
  completion: Record<DemoStepId, boolean>;
};

export function DemoStepper({ completion }: DemoStepperProps) {
  const activeStep = DEMO_STEPS.find((step) => !completion[step.id])?.id;

  return (
    <nav className="demo-stepper" aria-label="Demo progress">
      <ol className="demo-stepper-list">
        {DEMO_STEPS.map((step) => {
          const done = completion[step.id];
          const active = step.id === activeStep;
          const stateClass = done
            ? " demo-step-done"
            : active
              ? " demo-step-active"
              : "";
          return (
            <li
              key={step.id}
              className={`demo-step${stateClass}`}
              aria-current={active ? "step" : undefined}
            >
              <span className="demo-step-num" aria-hidden="true">
                {done ? <Icon name="check" size={12} /> : step.id}
              </span>
              <span className="demo-step-label">
                {step.label}
                {done && <span className="visually-hidden"> (done)</span>}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

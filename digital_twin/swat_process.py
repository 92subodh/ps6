"""
Digital Twin Process Model for SWaT Water Treatment System

Simplified physics-based simulation of the 6-stage SWaT testbed process.

Stages:
- P1: Raw water intake
- P2: Chemical dosing  
- P3: Ultrafiltration
- P4: Dechlorination
- P5: Reverse osmosis
- P6: Cleaning backwash

Author: GenTwin Team
Date: February 2026
"""

import numpy as np
from scipy.integrate import odeint
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ProcessConstraints:
    """Physical constraints for SWaT process."""
    
    # Tank level constraints (mm)
    LIT101_min: float = 800.0
    LIT101_max: float = 1200.0
    LIT301_min: float = 800.0
    LIT301_max: float = 1200.0
    LIT601_min: float = 800.0
    LIT601_max: float = 1200.0
    
    # Flow rate constraints (m³/h)
    flow_min: float = 0.0
    flow_max: float = 2.0
    
    # Chemical concentration constraints (mg/L)
    chlorine_min: float = 0.5
    chlorine_max: float = 3.0
    ph_min: float = 6.5
    ph_max: float = 8.5
    
    # Pump operational constraints
    pump_on_threshold: float = 0.5  # Binary threshold


class SWaTDigitalTwin:
    """
    Simplified process model of SWaT water treatment testbed.
    
    Models the physical dynamics of water flow, tank levels, and chemical processes
    across 6 stages. Used to validate impact of synthetic attacks.
    """
    
    def __init__(self, dt: float = 1.0):
        """
        Initialize digital twin.
        
        Args:
            dt: Simulation timestep in seconds
        """
        self.dt = dt
        self.constraints = ProcessConstraints()
        
        # Initialize state variables
        self.reset()
        
        # Track violations
        self.violation_history = []
        
    def reset(self):
        """Reset simulation to normal operating conditions."""
        self.state = {
            # P1: Raw water intake
            'LIT101': 1000.0,  # Tank level (mm)
            'FIT101': 1.5,     # Flow rate (m³/h)
            'P101_status': 1.0,  # Pump on
            'MV101_position': 0.5,  # Valve position (0-1)
            
            # P2: Chemical dosing
            'AIT201': 2.0,  # Chlorine concentration (mg/L)
            'AIT202': 7.0,  # pH
            'AIT203': 1.5,  # Flow rate
            'P201_status': 1.0,
            
            # P3: Ultrafiltration
            'LIT301': 1000.0,  # Tank level
            'FIT301': 1.0,     # Flow rate
            'MV301_position': 0.5,
            'MV302_position': 0.5,
            'MV303_position': 0.5,
            
            # P4: Dechlorination
            'AIT401': 0.5,  # Residual chlorine
            'AIT402': 7.2,  # pH
            'FIT401': 1.0,
            
            # P5: Reverse osmosis
            'AIT501': 200.0,  # Conductivity (μS/cm)
            'AIT502': 7.0,    # pH
            'AIT503': 3.0,    # Pressure (bar)
            'AIT504': 0.9,    # Flow rate
            'P501_status': 1.0,
            
            # P6: Backwash
            'LIT601': 1000.0,
            'FIT601': 0.5,
            'P601_status': 1.0,
            'P602_status': 0.0
        }
        
        self.time = 0.0
        self.violation_history = []
    
    def _tank_dynamics(self, 
                       level: float, 
                       inflow: float, 
                       outflow: float,
                       area: float = 1.0) -> float:
        """
        Calculate tank level change based on mass balance.
        
        Args:
            level: Current tank level (mm)
            inflow: Inflow rate (m³/h)
            outflow: Outflow rate (m³/h)
            area: Tank cross-sectional area (m²)
            
        Returns:
            Rate of level change (mm/s)
        """
        # Convert flow rate to mm/s
        # 1 m³/h = 1000000 mm³/h = 1000000/(3600) mm³/s
        # Level change = (inflow - outflow) / area
        
        flow_conversion = 1000000.0 / 3600.0  # m³/h to mm³/s
        net_flow = (inflow - outflow) * flow_conversion
        dlevel_dt = net_flow / (area * 1000000.0)  # Convert area to mm²
        
        return dlevel_dt
    
    def _pump_flow(self, pump_status: float, valve_position: float = 1.0) -> float:
        """
        Calculate pump output flow based on status and valve position.
        
        Args:
            pump_status: Pump on/off (0 or 1)
            valve_position: Valve opening (0-1)
            
        Returns:
            Flow rate (m³/h)
        """
        max_flow = 2.0  # Maximum pump capacity
        
        if pump_status > self.constraints.pump_on_threshold:
            return max_flow * valve_position
        else:
            return 0.0
    
    def step(self, sensor_values: Dict[str, float]) -> Dict:
        """
        Advance simulation by one timestep.
        
        Args:
            sensor_values: Dictionary of sensor/actuator values
            
        Returns:
            Updated state dictionary
        """
        # Update actuator states from sensor values
        for key, value in sensor_values.items():
            if key in self.state:
                self.state[key] = value
        
        # P1: Raw water intake dynamics
        p101_flow = self._pump_flow(self.state['P101_status'], self.state['MV101_position'])
        lit101_change = self._tank_dynamics(
            self.state['LIT101'],
            inflow=1.5,  # Constant source
            outflow=p101_flow
        )
        self.state['LIT101'] += lit101_change * self.dt
        self.state['FIT101'] = p101_flow
        
        # P2: Chemical dosing (simplified)
        # Chlorine concentration affected by dosing pump
        if self.state['P201_status'] > 0.5:
            # Dosing active - increase chlorine
            self.state['AIT201'] += 0.01 * self.dt
        else:
            # No dosing - chlorine decays
            self.state['AIT201'] -= 0.005 * self.dt
        
        self.state['AIT201'] = np.clip(self.state['AIT201'], 0.0, 5.0)
        
        # P3: Ultrafiltration dynamics
        p3_inflow = self.state['FIT101'] * self.state['MV301_position']
        p3_outflow = self.state['FIT301']
        lit301_change = self._tank_dynamics(
            self.state['LIT301'],
            inflow=p3_inflow,
            outflow=p3_outflow
        )
        self.state['LIT301'] += lit301_change * self.dt
        
        # P4: Dechlorination (chlorine removal)
        self.state['AIT401'] = max(0.0, self.state['AIT201'] - 1.5)
        
        # P5: Reverse osmosis (pressure and conductivity)
        if self.state['P501_status'] > 0.5:
            self.state['AIT503'] = 3.0  # Operating pressure
            self.state['AIT501'] = 150.0  # Low conductivity (good filtration)
        else:
            self.state['AIT503'] = 0.5  # Low pressure
            self.state['AIT501'] = 300.0  # High conductivity (poor filtration)
        
        # P6: Backwash dynamics
        p6_inflow = 0.3 if self.state['P602_status'] > 0.5 else 0.0
        p6_outflow = self._pump_flow(self.state['P601_status'])
        lit601_change = self._tank_dynamics(
            self.state['LIT601'],
            inflow=p6_inflow,
            outflow=p6_outflow
        )
        self.state['LIT601'] += lit601_change * self.dt
        
        # Increment time
        self.time += self.dt
        
        # Check for violations
        violations = self.check_safety_constraints()
        if violations:
            self.violation_history.append({
                'time': self.time,
                'violations': violations
            })
        
        return self.state.copy()
    
    def check_safety_constraints(self) -> List[Dict]:
        """
        Check for safety constraint violations.
        
        Returns:
            List of violation dictionaries
        """
        violations = []
        
        # Check tank levels
        tank_checks = [
            ('LIT101', self.constraints.LIT101_min, self.constraints.LIT101_max),
            ('LIT301', self.constraints.LIT301_min, self.constraints.LIT301_max),
            ('LIT601', self.constraints.LIT601_min, self.constraints.LIT601_max),
        ]
        
        for tank, min_val, max_val in tank_checks:
            level = self.state[tank]
            if level < min_val:
                violations.append({
                    'type': 'tank_underflow',
                    'sensor': tank,
                    'value': level,
                    'threshold': min_val,
                    'severity': 'high'
                })
            elif level > max_val:
                violations.append({
                    'type': 'tank_overflow',
                    'sensor': tank,
                    'value': level,
                    'threshold': max_val,
                    'severity': 'high'
                })
        
        # Check chemical concentrations
        if self.state['AIT201'] < self.constraints.chlorine_min:
            violations.append({
                'type': 'chlorine_low',
                'sensor': 'AIT201',
                'value': self.state['AIT201'],
                'threshold': self.constraints.chlorine_min,
                'severity': 'medium'
            })
        elif self.state['AIT201'] > self.constraints.chlorine_max:
            violations.append({
                'type': 'chlorine_high',
                'sensor': 'AIT201',
                'value': self.state['AIT201'],
                'threshold': self.constraints.chlorine_max,
                'severity': 'high'
            })
        
        # Check pH levels
        ph_sensors = ['AIT202', 'AIT402', 'AIT502']
        for sensor in ph_sensors:
            if sensor in self.state:
                ph = self.state[sensor]
                if ph < self.constraints.ph_min or ph > self.constraints.ph_max:
                    violations.append({
                        'type': 'ph_violation',
                        'sensor': sensor,
                        'value': ph,
                        'threshold': f"{self.constraints.ph_min}-{self.constraints.ph_max}",
                        'severity': 'medium'
                    })
        
        # Check for pump deadheading (pump on with closed valve)
        if self.state['P101_status'] > 0.5 and self.state['MV101_position'] < 0.1:
            violations.append({
                'type': 'pump_deadheading',
                'sensor': 'P101',
                'value': self.state['MV101_position'],
                'threshold': 0.1,
                'severity': 'high'
            })
        
        return violations
    
    def get_system_state(self) -> Dict:
        """
        Get current system state summary.
        
        Returns:
            Dictionary with state summary
        """
        return {
            'time': self.time,
            'state': self.state.copy(),
            'violations': self.check_safety_constraints(),
            'is_safe': len(self.check_safety_constraints()) == 0
        }
    
    def simulate(self, 
                 sensor_sequence: np.ndarray,
                 duration: int = 300) -> Dict:
        """
        Simulate system response to sensor sequence.
        
        Args:
            sensor_sequence: Array of sensor values over time
            duration: Simulation duration in seconds
            
        Returns:
            Dictionary with simulation results
        """
        self.reset()
        
        states = []
        violations_over_time = []
        
        for t in range(min(duration, len(sensor_sequence))):
            # Convert sensor array to dictionary (simplified - assumes mapping)
            sensor_dict = {f'sensor_{i}': val for i, val in enumerate(sensor_sequence[t])}
            
            # Step simulation
            state = self.step(sensor_dict)
            states.append(state.copy())
            
            # Check violations
            viols = self.check_safety_constraints()
            violations_over_time.append(len(viols))
        
        return {
            'states': states,
            'violations_per_step': violations_over_time,
            'total_violations': sum(violations_over_time),
            'violation_history': self.violation_history
        }


if __name__ == "__main__":
    # Test digital twin
    print("Testing SWaT Digital Twin...")
    
    dt = SWaTDigitalTwin(dt=1.0)
    
    print("\nInitial state:")
    state = dt.get_system_state()
    print(f"  Time: {state['time']}s")
    print(f"  Safe: {state['is_safe']}")
    print(f"  LIT101: {state['state']['LIT101']:.2f} mm")
    
    print("\nSimulating 60 seconds of normal operation...")
    for i in range(60):
        dt.step({})
    
    state = dt.get_system_state()
    print(f"  Time: {state['time']}s")
    print(f"  Safe: {state['is_safe']}")
    print(f"  LIT101: {state['state']['LIT101']:.2f} mm")
    
    print("\nSimulating attack scenario (close valve, keep pump on)...")
    for i in range(30):
        dt.step({'MV101_position': 0.0, 'P101_status': 1.0})
    
    state = dt.get_system_state()
    print(f"  Time: {state['time']}s")
    print(f"  Safe: {state['is_safe']}")
    print(f"  Violations: {len(state['violations'])}")
    if state['violations']:
        for v in state['violations']:
            print(f"    - {v['type']}: {v['sensor']} = {v['value']:.2f}")
    
    print("\nDigital Twin test complete!")

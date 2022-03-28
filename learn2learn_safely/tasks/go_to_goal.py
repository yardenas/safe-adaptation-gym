from typing import Mapping, Tuple

import numpy as np

import learn2learn_safely.utils as utils
from learn2learn_safely.mujoco_bridge import MujocoBridge
from learn2learn_safely.tasks.task import Task

import learn2learn_safely.primitive_objects as po


class GoToGoal(Task):
  GOAL_SIZE = 0.3
  GOAL_KEEPOUT = 0.305

  def __init__(self):
    self._last_goal_distance = None

  def setup_placements(self) -> Mapping[str, tuple]:
    return {'goal': (None, self.GOAL_KEEPOUT)}

  def build_world_config(self, layout: dict, rs: np.random.RandomState) -> dict:
    return {
        'geoms': {
            'goal':
                po.get_goal('goal', self.GOAL_SIZE, layout['goal'],
                            utils.random_rot(rs))
        }
    }

  def compute_reward(self, layout: dict, placements: dict,
                     rs: np.random.RandomState,
                     world: MujocoBridge) -> Tuple[float, dict]:
    goal_pos = np.asarray(world.body_pos('goal'))
    robot_pos = world.body_pos('robot')
    distance = np.linalg.norm(robot_pos - goal_pos)
    reward = self._last_goal_distance - distance
    self._last_goal_distance = distance
    info = {}
    if distance <= self.GOAL_SIZE:
      info['goal_met'] = True
      utils.update_layout(layout, world)
      self.build(layout, placements, rs, world)
      reward += 1.
    return reward, info

  def build(self, layout: dict, placements: dict, rs: np.random.RandomState,
            world: MujocoBridge):
    # TODO (yarden): possibly need to update the World's world config?
    goal_xy = self._resample_goal_position(layout, placements, rs)
    layout['goal'] = goal_xy
    robot_pos = world.body_pos('robot')
    self._last_goal_distance = np.linalg.norm(robot_pos - goal_xy)
    goal_body_id = world.model.name2id('goal', 'body')
    world.model.body_pos[goal_body_id][:2] = goal_xy
    world.sim.forward()

  def _resample_goal_position(self, layout: dict, placements: dict,
                              rs: np.random.RandomState):
    layout.pop('goal')
    for _ in range(10000):
      goal_xy = utils.draw_placement(rs, None, self.GOAL_KEEPOUT)
      for other_name, other_xy in layout.items():
        other_keepout = placements[other_name][1]
        dist = np.sqrt(np.sum(np.square(goal_xy - other_xy)))
        if dist >= other_keepout + self.GOAL_KEEPOUT:
          return goal_xy
    raise utils.ResamplingError('Failed to generate goal')
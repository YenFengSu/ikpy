# coding= utf8
import scipy.optimize
import numpy as np
from . import logs


ORIENTATION_COEFF = 1.


def inverse_kinematic_optimization(chain, target_frame, starting_nodes_angles, regularization_parameter=None, max_iter=None, orientation_mode=None):
    """
    Computes the inverse kinematic on the specified target with an optimization method

    Parameters
    ----------
    chain: ikpy.chain.Chain
        The chain used for the Inverse kinematics.
    target_frame: numpy.array
        The desired target.
    starting_nodes_angles: numpy.array
        The initial pose of your chain.
    regularization_parameter: float
        The coefficient of the regularization.
    max_iter: int
        Maximum number of iterations for the optimisation algorithm.
    orientation_mode: str
        Orientation to target. Choices:
        * None: No orientation
        * "X": Target the X axis
        * "Y": Target the Y axis
        * "Z": Target the Z axis
        * "all": Target the three axes
    """
    # Begin with the position
    target = target_frame[:3, -1]

    # Compute squared distance to target
    def optimize_target_function(x):
        # y = np.append(starting_nodes_angles[:chain.first_active_joint], x)
        y = chain.active_to_full(x, starting_nodes_angles)
        squared_distance_to_target = np.linalg.norm(chain.forward_kinematics(y)[:3, -1] - target)

        # We need to return y, it will be used in a later function
        return y, squared_distance_to_target

    if orientation_mode is None:
        def optimize_function(x):
            y, squared_distance_to_target = optimize_target_function(x)
            return squared_distance_to_target
    else:
        # Only get the first orientation vector
        if orientation_mode == "X":
            orientation = target_frame[:3, 0]

            def get_orientation(y):
                return chain.forward_kinematics(y)[:3, 0]

        elif orientation_mode == "Y":
            orientation = target_frame[:3, 1]

            def get_orientation(y):
                return chain.forward_kinematics(y)[:3, 1]

        elif orientation_mode == "Z":
            orientation = target_frame[:3, 2]

            def get_orientation(y):
                return chain.forward_kinematics(y)[:3, 2]

        elif orientation_mode == "all":
            orientation = target_frame[:3, :3]

            def get_orientation(y):
                return chain.forward_kinematics(y)[:3, :3]
        else:
            raise ValueError("Unknown orientation mode: {}".format(orientation_mode))

        def optimize_function(x):
            y, squared_distance_to_target = optimize_target_function(x)
            squared_distance_to_orientation = np.linalg.norm(get_orientation(y) - orientation)

            # Put more pressure on optimizing the distance to target, to avoid being stuck in a local minimum where the orientation is perfectly reached, but the target is nowhere to be reached
            squared_distance = squared_distance_to_target + ORIENTATION_COEFF * squared_distance_to_orientation

            return squared_distance

    if starting_nodes_angles is None:
        raise ValueError("starting_nodes_angles must be specified")

    # If a regularization is selected
    if regularization_parameter is not None:
        def optimize_total(x):
            regularization = np.linalg.norm(x - starting_nodes_angles[chain.first_active_joint:])
            return optimize_function(x) + regularization_parameter * regularization
    else:
        optimize_total = optimize_function

    # Compute bounds
    real_bounds = [link.bounds for link in chain.links]
    # real_bounds = real_bounds[chain.first_active_joint:]
    real_bounds = chain.active_from_full(real_bounds)

    options = {}
    # Manage iterations maximum
    if max_iter is not None:
        options["maxiter"] = max_iter

    # Utilisation d'une optimisation L-BFGS-B
    res = scipy.optimize.minimize(optimize_total, chain.active_from_full(starting_nodes_angles), method='L-BFGS-B', bounds=real_bounds, options=options)

    logs.logger.info("Inverse kinematic optimisation OK, done in {} iterations".format(res.nit))

    return chain.active_to_full(res.x, starting_nodes_angles)
    # return(np.append(starting_nodes_angles[:chain.first_active_joint], res.x))

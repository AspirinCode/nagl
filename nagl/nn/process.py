import abc

import dgl
import torch.nn


class PostprocessLayer(abc.ABC):
    """A layer to apply to the final readout of a neural network."""

    @abc.abstractmethod
    def forward(self, graph: dgl.DGLGraph, x: torch.Tensor) -> torch.Tensor:
        """Returns the post-processed input vector."""


class ComputePartialCharges(PostprocessLayer):
    """A layer which will map an NN readout containing a set of atomic electronegativity
    and hardness parameters to a set of partial charges [1].

    References:
        [1] Gilson, Michael K., Hillary SR Gilson, and Michael J. Potter. "Fast
            assignment of accurate partial atomic charges: an electronegativity
            equalization method that accounts for alternate resonance forms." Journal of
            chemical information and computer sciences 43.6 (2003): 1982-1997.
    """

    @classmethod
    def atomic_parameters_to_charges(
        cls,
        electronegativity: torch.Tensor,
        hardness: torch.Tensor,
        total_charge: float,
    ) -> torch.Tensor:
        """Converts a set of atomic electronegativity and hardness parameters to a
        set of partial atomic charges subject to a total charge constraint.

        Args:
            electronegativity: The electronegativity of atoms in a given molecule.
            hardness: The hardness of atoms in a given molecule.
            total_charge: The total charge on the molecule.

        Returns:
            The atomic partial charges.
        """

        inverse_hardness = 1.0 / hardness

        charges = (
            -inverse_hardness * electronegativity
            + inverse_hardness
            * torch.div(
                torch.dot(inverse_hardness, electronegativity) + total_charge,
                torch.sum(inverse_hardness),
            )
        ).reshape(-1, 1)

        return charges

    def forward(self, graph: dgl.DGLGraph, x: torch.Tensor) -> torch.Tensor:

        charges = []
        counter = 0

        for mol_graph in dgl.unbatch(graph):

            charges.append(
                self.atomic_parameters_to_charges(
                    x[counter : counter + len(mol_graph), 0],
                    x[counter : counter + len(mol_graph), 1],
                    0.0,
                )
            )
            counter += len(mol_graph)

        return torch.vstack(charges)

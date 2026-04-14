# SSGReps

This Python program can be used to compute representations of Spin-Space Groups (SSG).

## Getting Started

1. **Clone the repository:**

    ```bash
    git clone https://github.com/zine-phy/SSGReps.git
    ```

2. **Extract the data in `ssg_data`:**

    ```bash
    tar -xzvf identify.pkl.tar.gz
    ```

3. **Install the necessary libraries:**

    Generally, installing `pymatgen` will install all the dependencies.

    ```bash
    pip install pymatgen==2022.0.17
    ```

## Usage

Run the main program `SSGReps.py`:


    python SSGReps.py --ssgNum 194.1.6.1.P --kp 0 0 0.5 --out rep_matrix --groupType 1 --fileType json --optimize True > ssgrep.out

### Parameters

- `--ssgNum` (required): Specifies the SSG number.
- `--kp` (required): Specifies the k-point (the k-point is defined as the primitive cell with pure translation operations of the SSG).
- `--out` (optional): Specifies the output type, which can be `character` (default), `rep_degree`, or `rep_matrix`. 
  - `character`: Outputs the character table.
  - `rep_degree`: Outputs the degree of the representation.
  - `rep_matrix`: Outputs the representation matrix.
- `--groupType` (optional): Specifies the group type, either `2` for double group (default) or `1` for single group.
- `--fileType` (optional): Specifies the output file type. Options are:
  - `json`: Save output as a JSON file.
  - `npy`: Save output as a NumPy `.npy` file.
  - `None` (default): Only print output to the terminal.
- `--optimize` (optional): Optimize SSG representation matrices. Use `True` or `False` (default: `False`).



## Example

The folder `SG2SSG` contains a file `sg2ssg.dat` that lists all 230 space groups and their corresponding Spin-Space Groups (SSGs), representing first-class magnetic groups. This data can be used to verify that the program correctly reproduces the representations of space groups.

### Example: Space Group 63

Space group 63 corresponds to the SSG `63.1.4.67`. To compute the double-valued representation character table for this space group, use the following command:


    python SSGReps.py --ssgNum 63.1.4.67 --kp 0 0 0.5 --out character --groupType 2 > sg63.out

## References

This program relies on the following libraries and data sources:

1. **Spglib:**  
   Used for symmetry analysis.  
   > Togo, A., Shinohara, K., & Tanaka, I. (2024). *Spglib: a software library for crystal symmetry search*. *Sci. Technol. Adv. Mater., Meth.*, 4(1), 2384822–2384836. DOI: [10.1080/27660400.2024.2384822](https://doi.org/10.1080/27660400.2024.2384822).

2. **Pymatgen:**  
   Used for materials analysis and point group operations.  
   > Brown, P. J., Nunez, V., Tasset, F., Forsyth, J. B., & Radhakrishna, P. (1990). *Determination of the magnetic structure of Mn3Sn using generalized neutron polarization analysis*. *Computational Materials Science*, 2(47), 9409. DOI: [10.1088/0953-8984/2/47/015](https://dx.doi.org/10.1088/0953-8984/2/47/015).

3. **SSG Data Source:**  
   The spin-space group (SSG) data used in this program is based on the following work:  
   > Jiang, Y., Song, Z., Zhu, T., Fang, Z., Weng, H., Liu, Z.-X., Yang, J., & Fang, C. (2024). *Enumeration of Spin-Space Groups: Toward a Complete Description of Symmetries of Magnetic Orders*. *Phys. Rev. X, 14*(3), 031039. DOI: [10.1103/PhysRevX.14.031039](https://link.aps.org/doi/10.1103/PhysRevX.14.031039).

## License

This project is licensed under the terms of the [MIT License](LICENSE).  
You are free to use, modify, and distribute this software in compliance with the license terms.
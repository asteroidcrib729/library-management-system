#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <vector>
#include <cstdio>

using namespace std;

struct User_DATATYPE {
    string Username, Password;
};

struct DATATYPE {
    string title, author;
    int year;
    bool Reserved;
};

struct USER_DATATYPE {
    string Username, Password;
};

struct FINE_DATATYPE {
    string Username;
    int Fine;
};

struct Student {
    string name;
    int rollNumber;
    double feeBalance;

    Student(string name, int rollNumber, double feeBalance)
        : name(name), rollNumber(rollNumber), feeBalance(feeBalance) {}
};

vector<User_DATATYPE> user_data;
vector<DATATYPE> New_Allbooks;
vector<DATATYPE> Search_books;
vector<DATATYPE> Add_books;
vector<DATATYPE> Book_Remover;
vector<FINE_DATATYPE> Fine_Vec;
vector<string> Username_Vec;
vector<FINE_DATATYPE> Old_Data_Vec;
vector<FINE_DATATYPE> Search_Vec;
vector<FINE_DATATYPE> User_Fine_Read_Vec;
vector<FINE_DATATYPE> Clear_User_Fine_Vec;
vector<string> Search_Clear_Fine_User_Username_Vec;
vector<string> Fine_User_Username_vec;
vector<string> requestedBooks;
vector<string> feedbacks;

int addBook() {
    cout << "WELCOME TO THE ADD BOOK TO LIBRARY PAGE!" << endl << endl;
    DATATYPE book, book_read;
    bool Book_Exists = true;
    string line;

    ifstream Book_Read("LMS_Books_Metadata.txt");

    while (Book_Exists) {
        cout << "Enter the title of the book: ";
        getline(cin, book.title);
        Book_Exists = false;

        if (Book_Read.is_open()) {
            while (getline(Book_Read, line)) {
                size_t pos = line.find(",");
                book_read.title = line.substr(0, pos);
                line.erase(0, pos + 1);
                pos = line.find(",");
                book_read.author = line.substr(0, pos);
                line.erase(0, pos + 1);
                pos = line.find(":");
                stringstream ss(line);
                ss >> book_read.year;
                line.erase(0, pos + 1);
                stringstream(line.substr(0)) >> book_read.Reserved;

                if (book_read.title == book.title) {
                    Book_Exists = true;
                    cout << "BOOK ALREADY EXISTS IN THE LIBRARY! ADD A DIFFERENT BOOK!\n";
                }
            }
        }
        Book_Read.clear();            // Clear the end-of-file flag
        Book_Read.seekg(0, ios::beg); // Reset file pointer to the beginning for next iteration
    }
    Book_Read.close();

    cout << "Enter the name of the author: ";
    getline(cin, book.author);
    cout << "Enter the publication year: ";
    cin >> book.year;
    book.Reserved = false;
    Add_books.push_back(book);
    cin.ignore();
    ofstream Library("LMS_Books_Metadata.txt", ios_base::app);
    if (Library.is_open()) {
        for (int i = 0; i < Add_books.size(); i++) {
            Library << Add_books[i].title << "," << Add_books[i].author << "," << Add_books[i].year << ":" << Add_books[i].Reserved << endl;
            Library.close();
        }
        cout << "THE BOOK HAS BEEN ADDED TO THE LIBRARY!" << endl << endl;
    }
    else {
        cout << "UNABLE TO OPEN FILE!" << endl;
    }
    Add_books.clear();
    return 0;
}

void searchBooks() {
    DATATYPE book;
    string Search, Res, line;
    bool Found = false;
    ifstream Library("LMS_Books_Metadata.txt");
    cout << "WELCOME TO THE BOOK SEARCH PAGE!" << endl << endl;
    if (Library.is_open()) {
        cout << "ENTER TTITLE OF THE BOOK YOU WANT TO SEARCH FOR: ";
        getline(cin, Search);
        while (getline(Library, line)) {
            size_t pos = line.find(",");
            book.title = line.substr(0, pos);
            line.erase(0, pos + 1);
            pos = line.find(",");
            book.author = line.substr(0, pos);
            line.erase(0, pos + 1);
            pos = line.find(":");
            stringstream ss(line);
            ss >> book.year;
            line.erase(0, pos + 1);
            stringstream(line.substr(0)) >> book.Reserved;
            Search_books.push_back(book);
        }
        Library.close();
        for (int i = 0; i < Search_books.size(); i++) {
            if (Search_books[i].title == Search) {
                if (Search_books[i].Reserved == true) {
                    Res = "(This Book Is Reserved)";
                    cout << Search_books[i].title << " by " << Search_books[i].author << " (" << Search_books[i].year << ")" << ":" << Res << endl;
                    Found = true;
                    break;
                }
                else if (Search_books[i].Reserved == false) {
                    Res = "(This Book Is Available To Reserve)";
                    cout << Search_books[i].title << " by " << Search_books[i].author << " (" << Search_books[i].year << ")" << ":" << Res << endl;
                    Found = true;
                    Found = true;
                    break;
                }
            }
        }
        Search_books.clear();
        if (!Found) {
            cout << "NO BOOK FOUND WITH THE TITLE: \"" << Search << "\"" << endl;
        }
    }
    else {
        cout << "UNABLE TO OPEN FILE!" << endl;
    }
}

void displayAllBooks() {
    DATATYPE book;
    string line, Res;
    int count = 1;
    ifstream Library("LMS_Books_Metadata.txt");
    if (Library.is_open()) {
        cout << "BOOKS FOUND IN THE LIBRARY:" << endl << endl;
        while (getline(Library, line)) {
            size_t pos = line.find(",");
            book.title = line.substr(0, pos);
            line.erase(0, pos + 1);
            pos = line.find(",");
            book.author = line.substr(0, pos);
            line.erase(0, pos + 1);
            pos = line.find(":");
            stringstream ss(line);
            ss >> book.year;
            line.erase(0, pos + 1);
            stringstream(line.substr(0)) >> book.Reserved;
            if (book.Reserved == true) {
                Res = "(This Book Is Reserved)";
            }
            else {
                Res = "(This Book Is Available To Reserve)";
            }
            cout << count << ") " << book.title << " by " << book.author << " (" << book.year << ")" << ":" << Res << endl;
            count++;
        }
        Library.close();
    }
    else {
        cout << "UNABLE TO OPEN FILE!" << endl;
    }
}

int Book_Reservation() {
    DATATYPE book;
    string line, Search, Book_Reserve;
    cout << "To Reserve The Book, Enter \'Y\'. To Unreserve The Book, Enter \'X\'. Otherwise, Enter \'N\' To Exit." << endl;
    cout << "Enter Title Of The Book You Want To Reserve: ";
    getline(cin, Search);
    while (Book_Reserve != "N") {
        cout << "Enter A Character: ";
        cin >> Book_Reserve;
        if (Book_Reserve == "Y") {
            bool Found = false;
            ifstream LibraryInput("LMS_Books_Metadata.txt");
            if (LibraryInput.is_open()) {
                while (getline(LibraryInput, line)) {
                    size_t pos = line.find(",");
                    book.title = line.substr(0, pos);
                    line.erase(0, pos + 1);
                    pos = line.find(",");
                    book.author = line.substr(0, pos);
                    line.erase(0, pos + 1);
                    pos = line.find(":");
                    stringstream ss(line);
                    ss >> book.year;
                    line.erase(0, pos + 1);
                    stringstream(line.substr(0)) >> book.Reserved;
                    New_Allbooks.push_back(book);
                }
                LibraryInput.close();

                for (int i = 0; i < New_Allbooks.size(); i++) {
                    if (New_Allbooks[i].title == Search) {
                        if (New_Allbooks[i].Reserved != true) {
                            New_Allbooks[i].Reserved = true;
                            cout << "The Book Is Now Reserved." << endl;
                            Found = true;
                            break;
                        }
                        else if (New_Allbooks[i].Reserved == true) {
                            cout << "The Book Cannot Be Reserved At The Moment As It Has Already Been Reserved." << endl;
                            Found = true;
                            break;
                        }
                    }
                }

                if (Found) {
                    ofstream LibraryOutput("LMS_Books_Metadata_Updated.txt");
                    if (LibraryOutput.is_open()) {
                        for (int i = 0; i < New_Allbooks.size(); i++) {
                            LibraryOutput << New_Allbooks[i].title << "," << New_Allbooks[i].author << "," << New_Allbooks[i].year << ":" << New_Allbooks[i].Reserved << endl;
                        }
                        LibraryOutput.close();

                        const char* Oldfilename = "LMS_Books_Metadata.txt";
                        if (remove(Oldfilename) == 0) {}
                        else {
                            cout << "UNABLE TO DELETE FILE!" << endl;
                        }

                        if (std::rename("LMS_Books_Metadata_Updated.txt", "LMS_Books_Metadata.txt") == 0) {}
                        else {
                            cout << "UNABLE TO RENAME FILE!" << endl;
                        }
                        New_Allbooks.clear();
                    }
                    else {
                        cout << "UNABLE TO OPEN OUTPUT FILE!" << endl;
                    }
                }
                else {
                    cout << "BOOK NOT FOUND!" << endl;
                }
            }
            else {
                cout << "UNABLE TO OPEN INPUT FILE!" << endl;
            }
        }
        else if (Book_Reserve == "X") {
            bool Found = false;
            ifstream LibraryInput("LMS_Books_Metadata.txt");
            if (LibraryInput.is_open()) {
                while (getline(LibraryInput, line)) {
                    size_t pos = line.find(",");
                    book.title = line.substr(0, pos);
                    line.erase(0, pos + 1);
                    pos = line.find(",");
                    book.author = line.substr(0, pos);
                    line.erase(0, pos + 1);
                    pos = line.find(":");
                    stringstream ss(line);
                    ss >> book.year;
                    line.erase(0, pos + 1);
                    stringstream(line.substr(0)) >> book.Reserved;
                    New_Allbooks.push_back(book);
                }
                LibraryInput.close();

                for (int i = 0; i < New_Allbooks.size(); i++) {
                    if (New_Allbooks[i].title == Search) {
                        if (New_Allbooks[i].Reserved != false) {
                            New_Allbooks[i].Reserved = false;
                            cout << "The Book Is Now Unreserved." << endl;
                            Found = true;
                            break;
                        }
                        else if (New_Allbooks[i].Reserved == false) {
                            cout << "The Book Cannot Be Reserved At The Moment As It Has Already Been Unreserved." << endl;
                            Found = true;
                            break;
                        }
                    }
                }

                if (Found) {
                    ofstream LibraryOutput("LMS_Books_Metadata_Updated.txt");
                    if (LibraryOutput.is_open()) {
                        for (int i = 0; i < New_Allbooks.size(); i++) {
                            LibraryOutput << New_Allbooks[i].title << "," << New_Allbooks[i].author << "," << New_Allbooks[i].year << ":" << New_Allbooks[i].Reserved << endl;
                        }
                        LibraryOutput.close();
                        const char* Oldfilename = "LMS_Books_Metadata.txt";
                        if (remove(Oldfilename) == 0) {}
                        else {
                            cout << "UNABLE TO DELETE FILE!" << endl;
                        }

                        if (std::rename("LMS_Books_Metadata_Updated.txt", "LMS_Books_Metadata.txt") == 0) {}
                        else {
                            cout << "UNABLE TO RENAME FILE!" << endl;
                        }
                        New_Allbooks.clear();
                    }
                    else {
                        cout << "UNABLE TO OPEN OUTPUT FILE!" << endl;
                    }
                }
                else {
                    cout << "BOOK NOT FOUND!" << endl;
                }
            }
            else {
                cout << "UNABLE TO OPEN INPUT FILE!" << endl;
            }
        }
        else if (Book_Reserve == "N") {
            break;
        }
    }
    return 0;
}

int Book_Removal() {
    cout << "WELCOME TO THE BOOK REMOVAL PAGE!" << endl;
    DATATYPE Book_Remove_Data, Search_Book;
    bool Found = false;
    string line;
    cout << "ENTER NAME OF THE BOOK YOU WANT TO REMOVE: ";
    getline(cin, Search_Book.title);
    cout << Search_Book.title << endl;

    ifstream Read_Book_Data("LMS_Books_Metadata.txt");
    if (Read_Book_Data.is_open()) {
        while (getline(Read_Book_Data, line)) {
            size_t pos = line.find(",");
            Book_Remove_Data.title = line.substr(0, pos);
            line.erase(0, pos + 1);
            pos = line.find(",");
            Book_Remove_Data.author = line.substr(0, pos);
            line.erase(0, pos + 1);
            pos = line.find(":");
            stringstream ss(line);
            ss >> Book_Remove_Data.year;
            line.erase(0, pos + 1);
            stringstream(line.substr(0)) >> Book_Remove_Data.Reserved;
            Book_Remover.push_back(Book_Remove_Data);
        }
        Read_Book_Data.close();
    }
    else {
        cout << "UNABLE TO OPEN INPUT FILE!" << endl;
    }

    for (int i = 0; i < Book_Remover.size(); i++) {
        if (Book_Remover[i].title == Search_Book.title) {
            Book_Remover.erase(Book_Remover.begin() + i);
            cout << "THE BOOK WITH FOLLOWING TITLE: \"" << Search_Book.title << "\" HAS BEEN SUCCESSFULLY REMOVED." << endl;
            Found = true;
            break;
        }
    }
    if (!Found) {
        cout << "BOOK NOT FOUND!" << endl;
    }
    ofstream Write_Book_Data("LMS_Books_Metadata_Updated.txt");
    if (Write_Book_Data.is_open()) {
        for (int i = 0; i < Book_Remover.size(); i++) {
            Write_Book_Data << Book_Remover[i].title << "," << Book_Remover[i].author << "," << Book_Remover[i].year << ":" << Book_Remover[i].Reserved << endl;
        }
        Write_Book_Data.close();
        const char* Oldfilename = "LMS_Books_Metadata.txt";
        if (remove(Oldfilename) == 0) {}
        else {
            cout << "UNABLE TO DELETE FILE!" << endl;
        }

        if (std::rename("LMS_Books_Metadata_Updated.txt", "LMS_Books_Metadata.txt") == 0) {}
        else {
            cout << "UNABLE TO RENAME FILE!" << endl;
        }
        Book_Remover.clear();
    }
    else {
        cout << "UNABLE TO OPEN OUTPUT FILE!" << endl;
    }

    return 0;
}

int Fine_Admin() {
    char Admin_Input{};
    while (Admin_Input != 'E') {
        cout << "-------------------------------------------------------------------------\n";
        cout << "ENTER \'C\' TO CALCULATE USER\'S FINE.\nENTER \'E\' TO EXIT ADMIN FINE MANAGEMENT PAGE.\n";
        cout << "-------------------------------------------------------------------------\n";
        cout << "ENTER A CHARACTER: ";
        cin >> Admin_Input;
        if (Admin_Input == 'C') {
            int Total_Cost = 0, Fine_Per_Day = 10, Additional_Damage_Cost = 0, Cost_Book_Lost = 0, Additional_Days = 0;
            string Search_Username, line, check_line, Fine_Read_Line, LMS_User_Account_Data_Username;
            USER_DATATYPE User, Search_User;
            FINE_DATATYPE User_Fine, Fine_Read_Data;
            bool LMS_USER_ACCOUNT_DATABASE_FOUND = false, LMS_FINE_DATABASE_FOUND = false;
            ifstream Read("LMS_User_Account_Data.txt");
            ifstream Fine_Read("LMS_FINE_DATABASE.txt");
            cout << "ENTER USERNAME TO CALCULATE FINE: ";
            cin >> Search_Username;
            if (Read.is_open()) {
                while (getline(Read, check_line)) {
                    size_t position = check_line.find(",");
                    LMS_User_Account_Data_Username = check_line.substr(0, position);
                    check_line.erase(0, position + 1);
                    position = check_line.find(",");
                    check_line.erase(0, position + 1);
                    Username_Vec.push_back(LMS_User_Account_Data_Username);
                }
                Read.close();

                for (int i = 0; i < Username_Vec.size(); i++) {
                    if (Username_Vec[i] == Search_Username) {
                        LMS_USER_ACCOUNT_DATABASE_FOUND = true;
                        break;
                    }
                }

                if (Fine_Read.is_open()) {
                    while (getline(Fine_Read, Fine_Read_Line)) {
                        size_t pos = Fine_Read_Line.find(",");
                        Fine_Read_Data.Username = Fine_Read_Line.substr(0, pos);
                        Fine_Read_Line.erase(0, pos + 1);
                        pos = Fine_Read_Line.find(",");
                        stringstream FINE(Fine_Read_Line.substr(0, pos));
                        FINE >> Fine_Read_Data.Fine;
                        Old_Data_Vec.push_back(Fine_Read_Data);
                    }
                    Fine_Read.close();
                }
                else {
                    cout << "UNABLE TO OPEN INPUT FILE!\n" << endl;
                    return 0;
                }

                for (int i = 0; i < Old_Data_Vec.size(); i++) {
                    if (Old_Data_Vec[i].Username == Search_Username) {
                        LMS_FINE_DATABASE_FOUND = true;
                        break;
                    }
                }

                if (LMS_USER_ACCOUNT_DATABASE_FOUND && LMS_FINE_DATABASE_FOUND) {
                    cout << "THE USERNAME BEING ENTERED IS ALREADY ASSIGNED WITH FINE!\n" << endl;
                    return 0;
                }
                else if (LMS_USER_ACCOUNT_DATABASE_FOUND && !LMS_FINE_DATABASE_FOUND) {
                    cout << "ENTER THE NUMBER OF EXTRA DAYS THAT ARE EXCEEDING THE RETURN DEADLINE: ";
                    cin >> Additional_Days;
                    cout << "ENTER COST OF THE BOOK IF THE BOOK WAS LOST BY THE USER (OTHERWISE ENTER 0): ";
                    cin >> Cost_Book_Lost;
                    cout << "ENTER COST OF ADDITIONAL DAMAGES TO THE BOOK (ENTER 0 IF THERE WERE NO DAMAGES CAUSED BY THE USER): ";
                    cin >> Additional_Damage_Cost;
                    Total_Cost = (Fine_Per_Day * Additional_Days) + Additional_Damage_Cost + Cost_Book_Lost;
                    cout << "TOTAL CALCULATED FINE EQUALS: " << Total_Cost << endl;
                }
                else {
                    cout << "USER NOT FOUND!" << endl;
                    return 0;
                }
            }

            else {
                cout << "UNABLE TO OPEN INPUT FILE!\n" << endl;
                return 0;
            }

            for (int i = 0; i < Old_Data_Vec.size(); i++) {
                Fine_Vec.push_back(Old_Data_Vec[i]);
            }

            for (int i = 0; i < Fine_Vec.size(); i++) {
                if (Fine_Vec[i].Username == Search_Username) {
                    Fine_Vec.erase(Fine_Vec.begin() + i);
                    break;
                }
            }

            User_Fine.Username = Search_Username;
            User_Fine.Fine = Total_Cost;
            Fine_Vec.push_back(User_Fine);

            ofstream Write("LMS_FINE_DATABASE.txt");
            for (int i = 0; i < Fine_Vec.size(); i++) {
                Write << Fine_Vec[i].Username << "," << Fine_Vec[i].Fine << "," << endl;
            }
            Write.close();
        }
        else if (Admin_Input == 'E') {
            break;
        }
        else {
            cout << "WRONG INPUT! TRY AGAIN!\n";
        }
    }

    return 0;
}

int Fine_User() {
    cout << "-------------------------------------------------------------------------\n";
    cout << "ENTER \'D\' TO DISPLAY FINE.\nENTER \'C\' TO CLEAR FINE\nENTER \'E\' TO EXIT USER FINE MANAGEMENT PAGE.\n";
    cout << "-------------------------------------------------------------------------\n";
    string Search_Username;
    char User_Input_Var{};
    cout << "ENTER USERNAME: ";
    cin >> Search_Username;
    while (User_Input_Var != 'E') {
        cout << "-------------------------------------------------------------------------\n";
        cout << "ENTER \'D\' TO DISPLAY FINE.\nENTER \'C\' TO CLEAR FINE\nENTER \'E\' TO EXIT USER FINE MANAGEMENT PAGE.\n";
        cout << "-------------------------------------------------------------------------\n";
        cout << "ENTER A CHARACTER: ";
        cin >> User_Input_Var;
        cin.ignore();
        if (User_Input_Var == 'D') {
            ifstream Read("LMS_User_Account_Data.txt");
            ifstream Fine_Read("LMS_FINE_DATABASE.txt");
            string Fine_Line, User_Account_Line, LMS_User_Account_Data_Username;
            FINE_DATATYPE User_Fine_Read_Struc;
            bool USER_FINE_FOUND = false, USER_ACCOUNT_FOUND = false;
            if (Read.is_open()) {
                while (getline(Read, User_Account_Line)) {
                    size_t position = User_Account_Line.find(",");
                    LMS_User_Account_Data_Username = User_Account_Line.substr(0, position);
                    User_Account_Line.erase(0, position + 1);
                    position = User_Account_Line.find(",");
                    User_Account_Line.erase(0, position + 1);
                    Fine_User_Username_vec.push_back(LMS_User_Account_Data_Username);
                }
                Read.close();

                for (int a = 0; a < Fine_User_Username_vec.size(); a++) {
                    if (Fine_User_Username_vec[a] == Search_Username) {
                        USER_ACCOUNT_FOUND = true;
                        break;
                    }
                }

                if (USER_ACCOUNT_FOUND) {
                    if (Fine_Read.is_open()) {
                        while (getline(Fine_Read, Fine_Line)) {
                            size_t pos = Fine_Line.find(",");
                            User_Fine_Read_Struc.Username = Fine_Line.substr(0, pos);
                            Fine_Line.erase(0, pos + 1);
                            pos = Fine_Line.find(",");
                            stringstream Fine_Var_Read(Fine_Line.substr(0, pos));
                            Fine_Var_Read >> User_Fine_Read_Struc.Fine;
                            Fine_Line.erase(0, pos + 1);
                            User_Fine_Read_Vec.push_back(User_Fine_Read_Struc);
                        }
                        Fine_Read.close();
                    }

                    for (int i = 0; i < User_Fine_Read_Vec.size(); i++) {
                        if (User_Fine_Read_Vec[i].Username == Search_Username) {
                            cout << "THE USER ACCOUNT \"" << User_Fine_Read_Vec[i].Username << "\" HAS " << User_Fine_Read_Vec[i].Fine << " PKR OF DUE FINE.\n";
                            USER_FINE_FOUND = true;
                            break;
                        }
                    }

                    if (!USER_FINE_FOUND) {
                        cout << "THE USER ACCOUNT \"" << Search_Username << "\" DOES NOT HAVE ANY FINE DUE!\n";
                    }
                }

                else if (!USER_ACCOUNT_FOUND) {
                    cout << "USER NOT FOUND! ENTER A VALID USERNAME!\n";
                }
            }

            else {
                cout << "UNABLE TO OPEN INPUT FILE!\n" << endl;
                return 0;
            }

            Fine_User_Username_vec.clear();
            User_Fine_Read_Vec.clear();
        }

        else if (User_Input_Var == 'C') {
            ifstream Read("LMS_User_Account_Data.txt");
            ifstream Fine_Read("LMS_FINE_DATABASE.txt");
            string Clear_Line, User_Account_Line, LMS_User_Account_Data_Username;
            FINE_DATATYPE User_Fine_Read_Struc;
            bool Clear_Username_Found = false, USER_ACCOUNT_FOUND = false;

            if (Read.is_open()) {
                while (getline(Read, User_Account_Line)) {
                    size_t position = User_Account_Line.find(",");
                    LMS_User_Account_Data_Username = User_Account_Line.substr(0, position);
                    User_Account_Line.erase(0, position + 1);
                    position = User_Account_Line.find(",");
                    User_Account_Line.erase(0, position + 1);
                    Search_Clear_Fine_User_Username_Vec.push_back(LMS_User_Account_Data_Username);
                }
                Read.close();

                for (int a = 0; a < Search_Clear_Fine_User_Username_Vec.size(); a++) {
                    if (Search_Clear_Fine_User_Username_Vec[a] == Search_Username) {
                        USER_ACCOUNT_FOUND = true;
                        break;
                    }
                }
            }

            else {
                cout << "UNABLE TO OPEN INPUT FILE!\n" << endl;
                return 0;
            }

            if (USER_ACCOUNT_FOUND) {
                if (Fine_Read.is_open()) {
                    while (getline(Fine_Read, Clear_Line)) {
                        size_t pos = Clear_Line.find(",");
                        User_Fine_Read_Struc.Username = Clear_Line.substr(0, pos);
                        Clear_Line.erase(0, pos + 1);
                        pos = Clear_Line.find(",");
                        stringstream Fine_Var_Read(Clear_Line.substr(0, pos));
                        Fine_Var_Read >> User_Fine_Read_Struc.Fine;
                        Clear_Line.erase(0, pos + 1);
                        Clear_User_Fine_Vec.push_back(User_Fine_Read_Struc);
                    }
                    Fine_Read.close();
                }

                for (int i = 0; i < Clear_User_Fine_Vec.size(); i++) {
                    if (Clear_User_Fine_Vec[i].Username == Search_Username) {
                        Clear_User_Fine_Vec.erase(Clear_User_Fine_Vec.begin() + i);
                        Clear_Username_Found = true;
                        break;
                    }
                }

                ofstream Write_Updated_Fine("LMS_FINE_DATABASE.txt");
                for (int i = 0; i < Clear_User_Fine_Vec.size(); i++) {
                    Write_Updated_Fine << Clear_User_Fine_Vec[i].Username << "," << Clear_User_Fine_Vec[i].Fine << "," << endl;
                }

                if (Clear_Username_Found) {
                    cout << "THE USER ACCOUNT WITH USERNAME \"" << Search_Username << "\" HAS BEEN CLEARED OF FINE!\n";
                }

                else if (!Clear_Username_Found) {
                    cout << "THE USER ACCOUNT WITH USERNAME \"" << Search_Username << "\" IS ALREADY CLEAR OF FINE!\n";
                }
            }

            else if (!USER_ACCOUNT_FOUND) {
                cout << "USER NOT FOUND! ENTER A VALID USERNAME!\n";
            }

            Search_Clear_Fine_User_Username_Vec.clear();
            Clear_User_Fine_Vec.clear();
        }

        else if (User_Input_Var == 'E') {
            break;
        }

        else {
            cout << "WRONG INPUT! TRY AGAIN!\n";
        }
    }
    return 0;
}

void addStudent(vector<Student>& students) {
    string name;
    int rollNumber;
    double feeBalance;

    cout << "Enter student name: ";
    getline(cin, name);
    cout << "Enter roll number: ";
    cin >> rollNumber;
    cout << "Enter fee balance: ";
    cin >> feeBalance;

    cin.ignore(); // Clear input buffer

    students.push_back(Student(name, rollNumber, feeBalance));
    cout << "Student added successfully!" << endl;
}

void displayStudents(const vector<Student>& students) {
    if (students.empty()) {
        cout << "No students to display." << endl;
        return;
    }

    cout << "Student List:" << endl;
    for (const auto& student : students) {
        cout << "Name: " << student.name << endl;
        cout << "Roll Number: " << student.rollNumber << endl;
        cout << "Fee Balance: " << student.feeBalance << endl;
        cout << "---------------------" << endl;
    }
}

void updateFeeBalance(vector<Student>& students) {
    int rollNumber;
    double newFeeBalance;

    cout << "Enter roll number of the student: ";
    cin >> rollNumber;
    cout << "Enter new fee balance: ";
    cin >> newFeeBalance;

    for (auto& student : students) {
        if (student.rollNumber == rollNumber) {
            student.feeBalance = newFeeBalance;
            cout << "Fee balance updated successfully!" << endl;
            return;
        }
    }

    cout << "Student with roll number " << rollNumber << " not found." << endl;
}

void deleteStudent(vector<Student>& students) {
    int rollNumber;

    cout << "Enter roll number of the student to delete: ";
    cin >> rollNumber;

    for (auto it = students.begin(); it != students.end(); ++it) {
        if (it->rollNumber == rollNumber) {
            students.erase(it);
            cout << "Student deleted successfully!" << endl;
            return;
        }
    }

    cout << "Student with roll number " << rollNumber << " not found." << endl;
}

int Fees_Management() {
    vector<Student> students;
    int choice = 0;

    while (choice != 5) {
        cout << "---------------------" << endl;
        cout << "Fee Management Menu" << endl;
        cout << "1. Add Student" << endl;
        cout << "2. Display Students" << endl;
        cout << "3. Update Fee Balance" << endl;
        cout << "4. Delete Student" << endl;
        cout << "5. Exit" << endl;
        cout << "Enter your choice: ";
        cin >> choice;
        cin.ignore(); // Clear input buffer

        switch (choice) {
        case 1:
            addStudent(students);
            break;
        case 2:
            displayStudents(students);
            break;
        case 3:
            updateFeeBalance(students);
            break;
        case 4:
            deleteStudent(students);
            break;
        case 5:
            cout << "Exiting..." << endl;
            return 0;
        default:
            cout << "Invalid choice. Please try again." << endl;
        }
        cout << endl;
    }
    return 0;
}

void request_books() {
    int tcount = 0, choice = 0;
    while (choice != 2) {
        cout << "1. Request a book\n2. Exit\n";
        cout << "\nEnter Choice: ";
        cin >> choice;
        if (choice == 1) {
            string bookTitle, bookAuthor, bookPublicationYear;
            cout << "Enter the Title of the Requested Book: ";
            cin.ignore();
            getline(cin, bookTitle);
            cout << "Enter the Author of the Book: ";
            getline(cin, bookAuthor);
            cout << "Enter the Publication Year of the Book: ";
            cin >> bookPublicationYear;

            // Check if the book is already in the list
            bool isNewBook = true;
            for (int i = 0; i < requestedBooks.size(); i++) {
                if (requestedBooks[i] == bookTitle && requestedBooks[i] == bookAuthor && requestedBooks[i] == bookPublicationYear) {
                    isNewBook = false;
                    break;
                }
            }

            // If the book is not already in the list, add it to the list
            if (isNewBook) {
                requestedBooks.push_back(bookTitle);
                requestedBooks.push_back(bookAuthor);
                requestedBooks.push_back(bookPublicationYear);
                tcount++;
                cout << "\nResponse Submitted Successfully!\n";

                // Write the book details to a .txt file
                fstream myfile;
                myfile.open("LMS_REQUESTED_BOOKS_DATA.txt", ios::app);
                myfile << bookTitle << " " << bookAuthor << " " << bookPublicationYear << endl;
                myfile.close();
            }
            else {
                cout << "\nBook already requested.\n";
            }
        }
        else if (choice == 2) {
            cout << "Exiting....\n";
            break;
        }
        else {
            cout << "Wrong Input! Try Again!\n";
        }
    }
}

int User_Feedback() {
    string feedback_text, feedback;
    cout << "ENTER YOUR FEEDBACK HERE (TYPE \'exit\' TO STOP):" << endl;

    while (feedback_text != "exit") {
        getline(cin, feedback_text);

        if (feedback_text == "exit") {
            break;
        }

        feedbacks.push_back(feedback_text);
    }

    ofstream outputFile("LMS_USER_FEEDBACK.txt", ios::app);

    if (outputFile.is_open()) {
        for (int i = 0; i < feedbacks.size(); i++) {
            outputFile << feedbacks[i] << endl;
        }
        outputFile.close();
        feedbacks.clear();

        cout << "YOUR FEEDBACK HAS BEEN WRITTEN TO THE FILE SUCCESSFULLY." << endl;
    }

    else {
        cout << "UNABLE TO OPEN FILE!" << endl;
    }
    return 0;
}

int Book_Recommendation() {
    vector<string> Book_Names;

    string line;
    ifstream Read("LMS_Books_Metadata.txt");
    if (Read.is_open()) {
        while (getline(Read, line)) {
            size_t pos = line.find(",");
            string Book_Title = line.substr(0, pos);
            line.erase(0, pos + 1);
            pos = line.find("0");
            line.erase(0, pos + 1);
            Book_Names.push_back(Book_Title);
        }

        // Initialize random seed
        srand(time(0));

        // Generate a random index within the range of the vector
        int randomIndex = rand() % Book_Names.size();

        // Get the randomly selected name
        string randomName = Book_Names[randomIndex];

        // Display the recommendation to the user
        cout << "TODAY\'S BOOK RECOMMENDATION: " << randomName << endl;

        Read.close();
    }
    else {
        cout << "UNABLE TO OPEN FILE!\n";
    }
    return 0;
}

int User_Function() {
    char Choice_Input{};
    while (Choice_Input != 'E') {
        cout << "--------------------------------------------------\n";
        cout << "ENTER \'A\' TO DISPLAY ALL BOOKS.\nENTER \'B\' TO SEARCH FOR A BOOK.\nENTER \'C\' TO RESERVE A BOOK.\nENTER \'D\' FOR USER FINE MANAGEMENT PAGE.\nENTER \'F\' FOR USER BOOK REQUEST PAGE.\nENTER \'G\' FOR USER FEEDBACK PAGE.\nENTER \'H\' FOR BOOK RECOMMENDATION PAGE.\n";
        cout << "--------------------------------------------------\nENTER \'E\' TO EXIT THE SIGN-IN PAGE.\n--------------------------------------------------\n";
        cout << endl << "Enter A Character: ";
        cin >> Choice_Input;
        cin.ignore();
        switch (Choice_Input) {
        case 'A':
            displayAllBooks();
            break;
        case 'B':
            searchBooks();
            break;
        case 'C':
            Book_Reservation();
            break;
        case 'D':
            Fine_User();
            break;
        case 'F':
            request_books();
            break;
        case 'G':
            User_Feedback();
            break;
        case 'H':
            Book_Recommendation();
            break;
        case 'E':
            cout << "YOU HAVE EXITED THE SIGN-IN PAGE!" << endl << endl;
            break;
        }
    }
    return 0;
}

int Admin_Function() {
    char Choice_Input{};
    while (Choice_Input != 'E') {
        cout << "--------------------------------------------------\n";
        cout << "ENTER \'A\' TO ADD A BOOK TO THE LIBRARY.\nENTER \'B\' TO SEARCH FOR A BOOK.\nENTER \'C\' TO DISPLAY ALL BOOKS.\nENTER \'D\' TO REMOVE A BOOK FROM THE LIBARY\nENTER \'F\' FOR ADMIN FINE MANAGEMENT PAGE.\nENTER \'G\' FOR FEES MANAGEMENT PAGE.\n";
        cout << "--------------------------------------------------\nENTER \'E\' TO EXIT THE SIGN-IN PAGE.\n--------------------------------------------------\n";
        cout << endl << "Enter A Character: ";
        cin >> Choice_Input;
        cin.ignore();
        switch (Choice_Input) {
        case 'A':
            addBook();
            break;
        case 'B':
            searchBooks();
            break;
        case 'C':
            displayAllBooks();
            break;
        case 'D':
            Book_Removal();
            break;
        case 'F':
            Fine_Admin();
            break;
        case 'G':
            Fees_Management();
            break;
        case 'E':
            cout << "YOU HAVE EXITED THE SIGN-IN PAGE!" << endl << endl;
            break;
        }
    }
    return 0;
}

int Sign_up_Admin() {
    User_DATATYPE A;
    string Name, Username, Password, line;
    bool Admin_Exists = true;
    cout << "WELCOME TO LIBRARY MANAGEMENT SYSTEM!" << endl;
    cout << "SIGN-UP TO CONTINUE!" << endl;
    cout << "ENTER YOUR NAME: ";
    cin.ignore();
    getline(cin, Name);

    ifstream Read("LMS_Admin_Account_Data.txt");

    while (Admin_Exists) {
        cout << "CREATE A USERNAME: ";
        cin >> Username;
        Admin_Exists = false;

        if (Read.is_open()) {
            while (getline(Read, line)) {
                size_t pos = line.find(",");
                A.Username = line.substr(0, pos);
                line.erase(0, pos + 1);
                pos = line.find(",");
                A.Password = line.substr(0, pos);
                line.erase(0, pos + 1);
                if (A.Username == Username) {
                    Admin_Exists = true;
                    cout << "USERNAME ALREADY EXISTS! PLEASE SELECT A DIFFERENT USERNAME!\n";
                }
            }
        }
        Read.clear();            // Clear the end-of-file flag
        Read.seekg(0, ios::beg); // Reset file pointer to the beginning for next iteration
    }
    Read.close();

    cout << "CREATE A PASSWORD (MAXIMUM 15 CHARACTERS!): ";
    cin >> Password;
    while (Password.length() > 15) {
        cout << "INVALID PASSWORD! TRY AGAIN!" << endl << "CREATE A PASSWORD: ";
        cin >> Password;
    }
    // Append the user information to the database file
    ofstream Write("LMS_Admin_Account_Data.txt", ios_base::app);
    Write << Username << "," << Password << "," << endl;

    cout << "SIGN-UP SUCCESSFUL!" << endl;
    return 0;
}

int Sign_in_Admin() {
    string Username, Password;
    cout << "Welcome To Library Management System!" << endl;
    cout << "Please Sign In To Continue!" << endl << endl;
    cout << "Enter Username: ";
    cin >> Username;
    cout << "Enter Password: ";
    cin >> Password;
    // Check if the username and password match the ones in the database
    ifstream file("LMS_Admin_Account_Data.txt");
    string line;
    bool found = false;
    while (getline(file, line)) {
        if (line == Username + "," + Password + ",") {
            found = true;
            break;
        }
    }
    if (found) {
        cout << "Welcome, " << Username << "!" << endl;
        cout << "YOU HAVE ENTERED THE SIGN-IN PAGE!" << endl;
        Admin_Function();
        return 0;
    }
    else if (!found) {
        cout << "INVALID USERNAME OR PASSWORD! TRY AGAIN!" << endl;
        return 1;
    }
}

int Sign_up_User() {
    User_DATATYPE U;
    string Name, Username, Password, line;
    bool User_Exists = true;

    cout << "WELCOME TO LIBRARY MANAGEMENT SYSTEM!" << endl;
    cout << "SIGN-UP TO CONTINUE!" << endl;
    cout << "ENTER YOUR NAME: ";
    cin.ignore();
    getline(cin, Name);

    ifstream Read("LMS_User_Account_Data.txt");

    while (User_Exists) {
        cout << "CREATE A USERNAME: ";
        cin >> Username;
        User_Exists = false;

        if (Read.is_open()) {
            while (getline(Read, line)) {
                size_t pos = line.find(",");
                U.Username = line.substr(0, pos);
                line.erase(0, pos + 1);
                pos = line.find(",");
                U.Password = line.substr(0, pos);
                line.erase(0, pos + 1);
                if (U.Username == Username) {
                    User_Exists = true;
                    cout << "USERNAME ALREADY EXISTS! PLEASE SELECT A DIFFERENT USERNAME!\n";
                }
            }
        }
        Read.clear();            // Clear the end-of-file flag
        Read.seekg(0, ios::beg); // Reset file pointer to the beginning for next iteration
    }
    Read.close();

    cout << "CREATE A PASSWORD (MAXIMUM 12 CHARACTERS!): ";
    cin >> Password;
    while (Password.size() > 12) {
        cout << "INVALID PASSWORD! TRY AGAIN!" << endl << "CREATE A PASSWORD: ";
        cin >> Password;
    }

    // Append the user information to the database file
    ofstream file("LMS_User_Account_Data.txt", ios_base::app);
    file << Username << "," << Password << "," << endl;

    cout << "SIGN-UP SUCCESSFUL!" << endl;
    return 0;
}


int User_account_removal() {
    cout << "WELCOME TO THE USER-ACCOUNT REMOVAL PAGE!";
    User_DATATYPE U; // Temporary user structure to read data from file
    bool Found = false;
    string search_username, search_password, line;
    cout << "ENTER USERNAME: ";
    cin.ignore();
    getline(cin, search_username);

    ifstream Read_User("LMS_User_Account_Data.txt");
    if (Read_User.is_open()) {
        while (getline(Read_User, line)) {
            size_t pos = line.find(",");
            U.Username = line.substr(0, pos);
            line.erase(0, pos + 1);
            pos = line.find(",");
            U.Password = line.substr(0, pos);
            line.erase(0, pos + 1);
            user_data.push_back(U);
        }
        Read_User.close();
    }
    else {
        cout << "UNABLE TO OPEN INPUT FILE!" << endl;
    }

    for (int i = 0; i < user_data.size(); i++) {
        if (user_data[i].Username == search_username) {
            user_data.erase(user_data.begin() + i);
            cout << "THE USER-ACCOUNT WITH FOLLOWING USERNAME: \"" << search_username << "\" HAS BEEN SUCCESSFULLY REMOVED." << endl;
            Found = true;
            break;
        }
    }
    if (!Found) {
        cout << "USER NOT FOUND!" << endl;
    }

    ofstream Write_User("LMS_User_Account_Data_Temp.txt");
    if (Write_User.is_open()) {
        for (int i = 0; i < user_data.size(); i++) {
            Write_User << user_data[i].Username << "," << user_data[i].Password << "," << endl;
        }
        Write_User.close();
        const char* Oldfilename = "LMS_User_Account_Data.txt";
        if (remove(Oldfilename) == 0) {}
        else {
            cout << "UNABLE TO DELETE FILE!" << endl;
        }

        if (std::rename("LMS_User_Account_Data_Temp.txt", "LMS_User_Account_Data.txt") == 0) {}
        else {
            cout << "UNABLE TO RENAME FILE!" << endl;
        }
        user_data.clear();
    }
    else {
        cout << "UNABLE TO OPEN OUTPUT FILE!" << endl;
    }

    return 0;
}

int Sign_in_User() {
    string Username, Password;
    cout << "WELCOME TO LIBRARY MANAGEMENT SYSTEM!" << endl << "SIGN-IN TO CONTINUE!" << endl << endl;
    cout << "ENTER USERNAME: ";
    cin >> Username;
    cout << "ENTER PASSWORD: ";
    cin >> Password;
    // Check if the username and password match the ones in the database
    ifstream file("LMS_User_Account_Data.txt");
    string line;
    bool found = false;
    while (getline(file, line)) {
        if (line == Username + "," + Password + ",") {
            found = true;
            break;
        }
    }
    if (found) {
        cout << "WELCOME, " << Username << "!" << endl;
        cout << "YOU HAVE ENTERED THE SIGN-IN PAGE!" << endl;
        User_Function();
    }
    else {
        cout << "INVALID USERNAME OR PASSWORD!" << endl;
    }
    return 0;
}

int main() {
    int Num_Input = 1000;
    cout << "--------------------------------------------------\n";
    cout << "FOR USER:\nENTER 1 FOR SIGN-UP PAGE.\nENTER 2 FOR SIGN-IN PAGE.\nENTER 3 FOR USER-ACCOUNT REMOVAL PAGE.\n";
    cout << "--------------------------------------------------\n";
    cout << "FOR ADMIN:\nENTER 4 FOR SIGN-UP PAGE.\nENTER 5 FOR SIGN-IN PAGE.\n";
    cout << "--------------------------------------------------\nENTER 0 TO EXIT.\n--------------------------------------------------\n";
    while (Num_Input != 0) {
        cout << "ENTER A NUMBER: ";
        cin >> Num_Input;
        switch (Num_Input) {
        case 1:
            Sign_up_User();
            break;
        case 2:
            Sign_in_User();
            break;
        case 3:
            User_account_removal();
            break;
        case 4:
            Sign_up_Admin();
            break;
        case 5:
            Sign_in_Admin();
            break;
        case 0:
            break;
        }
    }
    return 0;
}